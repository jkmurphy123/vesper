# main.py — Phase 2: personalities, persona prompt, image + balloon placement + chunked playback
from __future__ import annotations
import sys
import random
import yaml
from pathlib import Path
from typing import Dict, Any, List
from PyQt5.QtCore import QObject, pyqtSignal, QThread
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
            text = llm.generate(self.prompt, max_tokens=500)
        except Exception as e:
            self.error.emit(f"Generation failed: {e}")
            return
        self.finished.emit("ok", text)


def load_config(cfg_path: Path) -> dict:
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def pick_personality(cfg: Dict[str, Any]) -> Dict[str, Any]:
    plist = cfg.get("personalities", [])
    if not plist:
        return {}
    return random.choice(plist)


def build_phase2_prompt(persona: Dict[str, Any], topic: str) -> str:
    prompt_persona = persona.get("prompt_persona", "You are a distinct voice.")
    style_rules = persona.get("style_rules", [])
    examples = persona.get("examples", [])
    display_name = persona.get("display_name", persona.get("name", "Persona"))

    rules_formatted = "".join([f"- {r}" for r in style_rules])
    ex_formatted = "".join([f"Example — {display_name}: \"{e}\"" for e in examples])

    prompt = (
        f"{prompt_persona}"
        f"Style rules:{rules_formatted}"
        f"Reference tone/examples (do not repeat verbatim):{ex_formatted}"
        f"Write a monologue (~{persona.get('max_words_per_chunk', 85) * 3} words) about the topic: '{topic}'."
        f"Stay fully in character as {display_name}. Do not include stage directions or brackets."
    )
    return prompt


def chunk_text_by_words(text: str, max_words: int) -> List[str]:
    words = text.split()
    chunks: List[str] = []
    for i in range(0, len(words), max(1, max_words)):
        chunk = " ".join(words[i:i+max_words]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def main() -> int:
    cfg_path = Path(__file__).parent / "config.yaml"
    cfg = load_config(cfg_path)

    ui_cfg = cfg.get("ui", {})
    title = ui_cfg.get("window_title", "LLM Stream of Consciousness — Phase 2")

    width = int(ui_cfg.get("screen_width", 1024))
    height = int(ui_cfg.get("screen_height", 768))

    # === Personality selection and assets ===
    persona = pick_personality(cfg)
    if not persona:
        persona = {
            "display_name": "Default Persona",
            "image_file_name": "background_active.jpg",
            "speech_balloon": {"x_pos": 100, "y_pos": 100, "width": 600, "height": 300},
            "max_words_per_chunk": 85,
            "prompt_persona": "You are a thoughtful narrator.",
            "style_rules": ["Be clear and engaging."],
            "examples": ["A tiny example line."]
        }

    personality_img = persona.get("image_file_name", "background_active.jpg")
    bg_path = str(Path("assets") / personality_img)

    balloon_cfg = persona.get("speech_balloon", {})

    app = QApplication(sys.argv)
    window = ConversationWindow(
        title=title,
        background_path=bg_path,
        ui_cfg=ui_cfg,
        balloon_cfg=balloon_cfg,
        design_size={"screen_width": ui_cfg.get("screen_width", 1024), "screen_height": ui_cfg.get("screen_height", 768)},
    )
    window.resize(width, height)
    window.show()
    window.show_status(f"Persona: {persona.get('display_name', persona.get('name', 'Persona'))} • Generating…")

    topic = "amusement parks"
    prompt = build_phase2_prompt(persona, topic)

    model_path = cfg.get("model_path")

    thread = QThread()
    worker = LLMWorker(model_path=model_path, prompt=prompt)
    worker.moveToThread(thread)

    def on_started():
        window.show_status("Generating in character…")

    def on_finished(status: str, text: str):
        max_words = int(persona.get('max_words_per_chunk', 85))
        chunks = chunk_text_by_words(text, max_words)
        if not chunks:
            window.display_text("[Empty response]")
            window.show_status("No content returned")
        else:
            window.play_chunks(chunks, delay_seconds=30)
            window.show_status(f"Showing {len(chunks)} chunks • {max_words} words each")
        thread.quit(); thread.wait()

    def on_error(msg: str):
        window.display_text(f"[LLM error] {msg} Check model_path in config.yaml and your llama-cpp-python install.")
        window.show_status("Error — see text.")
        thread.quit(); thread.wait()

    thread.started.connect(on_started)
    thread.started.connect(worker.run)
    worker.finished.connect(on_finished)
    worker.error.connect(on_error)
    thread.start()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())