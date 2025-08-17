# main.py
from __future__ import annotations
import sys
import yaml
from pathlib import Path
from PyQt5.QtCore import QTimer, QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication

from ui_renderer import ConversationWindow
from llm_interface import LLMInterface


class LLMWorker(QObject):
    finished = pyqtSignal(str, str)  # (status, text)
    error = pyqtSignal(str)

    def __init__(self, model_path: str, prompt: str):
        super().__init__()
        self.model_path = model_path
        self.prompt = prompt

    def run(self):
        try:
            llm = LLMInterface(
                model_path=self.model_path,
                n_gpu_layers=-1,
                n_ctx=4096,
                temperature=0.7,
                top_p=0.95,
            )
        except Exception as e:
            self.error.emit(f"LLM init failed: {e}")
            return
        try:
            text = llm.generate(self.prompt, max_tokens=200)
        except Exception as e:
            self.error.emit(f"Generation failed: {e}")
            return
        self.finished.emit("ok", text)


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

    width = int(ui_cfg.get("screen_width", 1000))
    height = int(ui_cfg.get("screen_height", 700))
    startup_bg = ui_cfg.get("startup_background", ui_cfg.get("background_image", "assets/background.jpg"))
    active_bg = ui_cfg.get("active_background", ui_cfg.get("ready_background", startup_bg))
    print(f"[DEBUG] Window size = {width}x{height}, startup_bg = {startup_bg}, active_bg = {active_bg}")

    app = QApplication(sys.argv)

    window = ConversationWindow(title=title, background_path=str(Path(startup_bg)), ui_cfg=ui_cfg)
    window.resize(width, height)
    window.show()
    window.show_status("App started • Initializing LLM in background…")

    # Spin up worker thread so UI stays responsive and paints startup image
    model_path = cfg.get("model_path")
    prompt = build_phase1_prompt()

    thread = QThread()
    worker = LLMWorker(model_path=model_path, prompt=prompt)
    worker.moveToThread(thread)

    def on_started():
        print("[DEBUG] Worker thread started")
        window.show_status("LLM initializing…")

    def on_finished(status: str, text: str):
        print("[DEBUG] Worker finished; updating UI")
        window.set_background(str(Path(active_bg)))
        window.display_text(text)
        window.show_status("Generation complete ✔︎")
        thread.quit()
        thread.wait()

    def on_error(msg: str):
        print(f"[DEBUG] Worker error: {msg}")
        window.display_text(f"[LLM error] {msg} Check model_path in config.yaml and your llama-cpp-python install.")
        window.show_status("Error — see text.")
        thread.quit()
        thread.wait()

    thread.started.connect(on_started)
    thread.started.connect(worker.run)
    worker.finished.connect(on_finished)
    worker.error.connect(on_error)
    thread.start()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())