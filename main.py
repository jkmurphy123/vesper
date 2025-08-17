# main.py
from __future__ import annotations
import sys
import yaml
from pathlib import Path
from PyQt5.QtWidgets import QApplication

from ui_renderer import ConversationWindow
from llm_interface import LLMInterface


def load_config(cfg_path: Path) -> dict:
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_phase1_prompt() -> str:
    return (
        "You are a helpful language model.
"
        "Write two short, friendly paragraphs (3-4 sentences total) saying hello and 
"
        "describing one whimsical thought you just had."
    )


def main() -> int:
    cfg = load_config(Path(__file__).parent / "config.yaml")

    ui_cfg = cfg.get("ui", {})
    title = ui_cfg.get("window_title", "LLM Stream of Consciousness — Phase 1")

    # Window size & backgrounds
    width = int(ui_cfg.get("screen_width", 1000))
    height = int(ui_cfg.get("screen_height", 700))
    startup_bg = ui_cfg.get("startup_background", ui_cfg.get("background_image", "assets/background.jpg"))
    active_bg = ui_cfg.get("active_background", startup_bg)

    app = QApplication(sys.argv)
    window = ConversationWindow(title=title, background_path=str(Path(startup_bg)), ui_cfg=ui_cfg)
    window.resize(width, height)  # ensure size on startup
    window.show()
    window.show_status("App started. Initializing LLM…")

    # Initialize the local LLM
    model_path = cfg.get("model_path")
    try:
        llm = LLMInterface(
            model_path=model_path,
            n_gpu_layers=-1,
            n_ctx=4096,
            temperature=0.7,
            top_p=0.95,
        )
        window.show_status("LLM initialized. Sending test prompt…")
    except Exception as e:
        window.display_text(f"[LLM error] {e}

Check model_path in config.yaml and your llama-cpp-python install.")
        window.show_status("Failed to initialize LLM.")
        return app.exec_()

    # Phase 1 test prompt
    prompt = build_phase1_prompt()
    try:
        text = llm.generate(prompt, max_tokens=200)
        # Switch background ONLY after a successful response, just before displaying text
        window.set_background(str(Path(active_bg)))
        window.show_status("LLM response received.")
    except Exception as e:
        text = f"[LLM error] {e}

Check model_path in config.yaml and your llama-cpp-python install."
        window.show_status("LLM generation failed.")

    window.display_text(text)
    window.show_status("Display updated.")
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())