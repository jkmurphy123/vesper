# main.py
from __future__ import annotations
import sys
import yaml
from pathlib import Path
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from ui_renderer import ConversationWindow
from llm_interface import LLMInterface


def load_config(cfg_path: Path) -> dict:
    print(f"[DEBUG] Loading config from {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    print(f"[DEBUG] Config loaded: {cfg}")
    return cfg


def build_phase1_prompt() -> str:
    return (
        "You are a helpful language model."
        "Write two short, friendly paragraphs (3-4 sentences total) saying hello and "
        "describing one whimsical thought you just had."
    )


def main() -> int:
    cfg_path = Path(__file__).parent / "config.yaml"
    print(f"[DEBUG] main() starting. Config path = {cfg_path}")
    cfg = load_config(cfg_path)

    ui_cfg = cfg.get("ui", {})
    print(f"[DEBUG] UI config: {ui_cfg}")
    title = ui_cfg.get("window_title", "LLM Stream of Consciousness — Phase 1")

    # Window size & backgrounds
    width = int(ui_cfg.get("screen_width", 1000))
    height = int(ui_cfg.get("screen_height", 700))
    startup_bg = ui_cfg.get("startup_background", ui_cfg.get("background_image", "assets/background.jpg"))
    active_bg = ui_cfg.get("active_background", ui_cfg.get("ready_background", startup_bg))
    print(f"[DEBUG] Window size = {width}x{height}, startup_bg = {startup_bg}, active_bg = {active_bg}")

    app = QApplication(sys.argv)

    window = ConversationWindow(title=title, background_path=str(Path(startup_bg)), ui_cfg=ui_cfg)
    window.resize(width, height)
    window.show()
    window.show_status("App started • Preparing to initialize LLM…")

    app.processEvents()

    def start_generation():
        print("[DEBUG] Entered start_generation()")
        window.show_status("Initializing LLM…")
        model_path = cfg.get("model_path")
        print(f"[DEBUG] Model path from config: {model_path}")
        try:
            llm = LLMInterface(
                model_path=model_path,
                n_gpu_layers=-1,
                n_ctx=4096,
                temperature=0.7,
                top_p=0.95,
            )
            print("[DEBUG] LLM initialized successfully")
            window.show_status("LLM ready • Sending test prompt…")
        except Exception as e:
            print(f"[DEBUG] LLM init failed: {e}")
            window.display_text(
                f"[LLM error] {e} Check model_path in config.yaml and your llama-cpp-python install."
            )
            window.show_status("LLM init failed ✖")
            return

        prompt = build_phase1_prompt()
        print(f"[DEBUG] Prompt built: {prompt[:60]}...")
        window.show_status("Generating… (this may take a moment)")
        try:
            text = llm.generate(prompt, max_tokens=200)
            print(f"[DEBUG] Generation succeeded. Text length = {len(text)}")
            window.set_background(str(Path(active_bg)))
            window.show_status("LLM response received • Updating display…")
        except Exception as e:
            print(f"[DEBUG] Generation failed: {e}")
            text = (
                f"[LLM error] {e} Check model_path in config.yaml and your llama-cpp-python install."
            )
            window.show_status("Generation failed ✖")

        window.display_text(text)
        window.show_status("Display updated ✔︎")

    QTimer.singleShot(0, start_generation)

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())