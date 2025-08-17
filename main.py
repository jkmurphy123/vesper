from __future__ import annotations
import sys
import random
import yaml
from pathlib import Path
from PyQt5.QtWidgets import QApplication

from ui_renderer import ConversationWindow
from llm_interface import LLMInterface


def load_config(cfg_path: Path) -> dict:
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_phase1_prompt() -> str:
    # Keep Phase 1 super simple — just confirm the model runs.
    return (
        "You are a helpful language model.\n"
        "Write two short, friendly paragraphs (3-4 sentences total) saying hello and \n"
        "describing one whimsical thought you just had."
    )


def main() -> int:
    cfg = load_config(Path(__file__).parent / "config.yaml")

    ui_cfg = cfg.get("ui", {})
    title = ui_cfg.get("window_title", "LLM Stream of Consciousness — Phase 1")
    bg_path = cfg.get("ui", {}).get("background_image", "assets/background.jpg")

    app = QApplication(sys.argv)
    window = ConversationWindow(title=title, background_path=str(Path(bg_path)), ui_cfg=ui_cfg)
    window.show()

    # Initialize the local LLM
    model_path = cfg.get("model_path")
    llm = LLMInterface(
        model_path=model_path,
        n_gpu_layers=-1,  # good starting point on Jetson CUDA build; adjust if you see OOM
        n_ctx=4096,
        temperature=0.7,
        top_p=0.95,
    )

    # Phase 1 test prompt
    prompt = build_phase1_prompt()
    try:
        text = llm.generate(prompt, max_tokens=200)
    except Exception as e:
        text = f"[LLM error] {e}\n\nCheck model_path in config.yaml and your llama-cpp-python install."

    window.display_text(text)
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())