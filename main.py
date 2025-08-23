# main.py — endless loop + LLM-picked visible topic (Jetson-safe: 1 model, 1 worker thread)
from __future__ import annotations
import sys, random, re, yaml
from pathlib import Path
from typing import Dict, Any, List
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, QTimer
from PyQt5.QtWidgets import QApplication

from ui_renderer import ConversationWindow
from llm_interface import LLMInterface


# ---------- Config helpers ----------
def load_config(cfg_path: Path) -> dict:
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def pick_persona_sequence(cfg: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
    all_personas = cfg.get("personalities", []) or []
    if not all_personas:
        return [{
            "display_name": "Default Persona",
            "image_file_name": "ready.jpg",
            "speech_balloon": {"x_pos": 100, "y_pos": 100, "width": 600, "height": 300},
            "max_words_per_chunk": 85,
            "prompt_persona": "You are a thoughtful narrator.",
            "style_rules": ["Be clear and engaging."],
            "examples": ["A tiny example line."]
        }]

    if len(all_personas) >= count:
        return random.sample(all_personas, count)
    return [random.choice(all_personas) for _ in range(count)]


# ---------- Prompt + chunking ----------
def build_prompt(persona: Dict[str, Any], topic: str) -> str:
    prompt_persona = persona.get("prompt_persona", "You are a distinct voice.")
    style_rules = persona.get("style_rules", [])
    examples = persona.get("examples", [])
    display_name = persona.get("display_name", persona.get("name", "Persona"))

    rules_formatted = "\n".join(f"- {r}" for r in style_rules)
    ex_formatted = "\n".join(f"Example — {display_name}: \"{e}\"" for e in examples)
    approx_words = int(persona.get("max_words_per_chunk", 85)) * 3

    return (
        f"{prompt_persona}\n\n"
        f"Style rules:\n{rules_formatted}\n\n"
        f"Reference tone/examples (do not repeat verbatim):\n{ex_formatted}\n\n"
        f"Write about the topic: '{topic}'. Aim for ~{approx_words} words in total.\n"
        f"Stay fully in character as {display_name}. Do not include stage directions or brackets.\n"
    )


def chunk_text_by_sentences(text: str, max_words: int) -> List[str]:
    """
    Group full sentences up to ~max_words per chunk.
    If a single sentence exceeds the cap, hard-split that sentence by words.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks: List[str] = []
    current: List[str] = []
    count = 0

    def flush():
        nonlocal current, count
        if current:
            chunks.append(" ".join(current).strip())
            current, count = [], 0

    for s in sentences:
        if not s:
            continue
        words = s.split()
        if not words:
            continue

        if len(words) > max_words:
            # Hard-split long sentence
            flush()
            for i in range(0, len(words), max_words):
                part = " ".join(words[i:i+max_words]).strip()
                if part:
                    chunks.append(part)
            continue

        if count + len(words) <= max_words:
            current.append(s)
            count += len(words)
        else:
            flush()
            current = [s]
            count = len(words)

    flush()
    return [c for c in chunks if c]


def build_topic_prompt() -> str:
    # Lightweight ask for a short, clean topic
    return (
        "Suggest exactly ONE random, creative topic for a character to muse about.\n"
        "- Output ONLY the topic text, 2–6 words.\n"
        "- No quotes, punctuation, labels, or explanations."
    )


# ---------- Worker (long-lived in one thread) ----------
class LLMWorker(QObject):
    finished = pyqtSignal(str)   # emits text
    error = pyqtSignal(str)

    def __init__(self, llm: LLMInterface):
        super().__init__()
        self.llm = llm

    @pyqtSlot(str, int)
    def generate(self, prompt: str, max_tokens: int = 700):
        try:
            text = self.llm.generate(prompt, max_tokens=max_tokens)
            self.finished.emit(text)
        except Exception as e:
            self.error.emit(str(e))


# ---------- Main ----------
def main() -> int:
    cfg_path = Path(__file__).parent / "config.yaml"
    cfg = load_config(cfg_path)

    ui_cfg = cfg.get("ui", {})
    title = ui_cfg.get("window_title", "LLM Stream of Consciousness — Phase 2")
    width = int(ui_cfg.get("screen_width", 1024))
    height = int(ui_cfg.get("screen_height", 768))
    num_chars = int(cfg.get("num_characters", 1))

    app = QApplication(sys.argv)

    # Build LLM on the MAIN THREAD (Jetson-safe)
    try:
        llm = LLMInterface(
            model_path=cfg.get("model_path"),
            n_gpu_layers=-1,  # set 0 for CPU-only while debugging stability
            n_ctx=4096,
            temperature=0.7,
            top_p=0.95,
        )
    except Exception as e:
        w = ConversationWindow(title=title,
                               background_path=str(Path(ui_cfg.get("startup_background", "assets/startup.jpg"))),
                               ui_cfg=ui_cfg)
        w.resize(width, height)
        w.show()
        w.display_text(f"[LLM error] {e}\n\nCheck model_path in config.yaml and your llama-cpp-python install.")
        w.show_status("Failed to initialize LLM.")
        return app.exec_()

    # Create window once
    init_bg = str(Path(ui_cfg.get("startup_background", "assets/startup.jpg")))
    window = ConversationWindow(
        title=title,
        background_path=init_bg,
        ui_cfg=ui_cfg,
        balloon_cfg={"x_pos": 100, "y_pos": 100, "width": 600, "height": 300},
        design_size={"screen_width": width, "screen_height": height},
    )
    window.resize(width, height)
    window.show()
    window.show_status("Starting… (ESC to quit)")

    # One long-lived worker thread
    thread = QThread()
    worker = LLMWorker(llm)
    worker.moveToThread(thread)
    thread.start()

    # Prepare persona sequence (endless loop will refresh this each pass)
    state = {"personas_seq": pick_persona_sequence(cfg, num_chars)}
    index = {"i": 0}

    def run_one():
        # End-of-pass: pick a fresh random set and continue forever
        if index["i"] >= len(state["personas_seq"]):
            window.show_status("Pass complete — picking new characters…")
            state["personas_seq"] = pick_persona_sequence(cfg, num_chars)
            index["i"] = 0

        i = index["i"]
        persona = state["personas_seq"][i]
        name = persona.get("display_name", persona.get("name", "Persona"))

        # Update background & balloon for this persona
        bg_path = str(Path("assets") / persona.get("image_file_name", ui_cfg.get("ready_background", "assets/ready.jpg")))
        window.set_background(bg_path)
        if hasattr(window, "set_balloon"):
            window.set_balloon(
                persona.get("speech_balloon", {"x_pos": 100, "y_pos": 100, "width": 600, "height": 300}),
                {"screen_width": width, "screen_height": height}
            )
        window.display_text("")  # clear
        window.show_status(f"Persona {i+1}/{len(state['personas_seq'])}: {name} • choosing topic…")

        # Guard so proceed_next can't double-fire
        guard = {"done": False}

        def proceed_next():
            if guard["done"]:
                return
            guard["done"] = True
            index["i"] += 1
            QTimer.singleShot(0, run_one)

        def on_error(msg: str):
            window.display_text(
                f"[LLM error] {msg}\n\nCheck model_path in config.yaml and your llama-cpp-python install."
            )
            window.show_status("Error — moving to next character")
            proceed_next()

        # STEP 1: Ask LLM for a random topic (visible to user)
        def on_topic_finished(text: str):
            # Clean topic: take first non-empty line, strip extra punctuation/quotes
            raw = (text or "").strip()
            topic = raw.splitlines()[0].strip().strip("\"'“”‘’.,;:- ") or "life"
            window.display_text(f"Topic: {topic}")
            window.show_status(f"{name}: topic chosen → {topic}")

            # After a brief beat, generate persona's musings on that topic
            def start_persona():
                prompt = build_prompt(persona, topic)

                def on_persona_finished(gen_text: str):
                    max_words = int(persona.get("max_words_per_chunk", 85))
                    chunks = chunk_text_by_sentences(gen_text, max_words)
                    if not chunks:
                        window.display_text("[Empty response]")
                        window.show_status("No content returned — moving on…")
                        proceed_next()
                        return

                    window.play_chunks(chunks, delay_seconds=30)
                    window.show_status(f"{name}: showing {len(chunks)} chunks • ≤{max_words} words each")

                    # Connect end-of-chunks -> next persona
                    try:
                        window.chunks_finished.disconnect()
                    except Exception:
                        pass
                    window.chunks_finished.connect(proceed_next)

                    # Fallback safety in case the signal never fires
                    total_ms = 30_000 * max(1, len(chunks))
                    QTimer.singleShot(total_ms + 2000, proceed_next)

                # Rewire worker for persona generation
                try:
                    worker.finished.disconnect()
                except Exception:
                    pass
                try:
                    worker.error.disconnect()
                except Exception:
                    pass
                worker.finished.connect(on_persona_finished)
                worker.error.connect(on_error)

                QTimer.singleShot(0, lambda: worker.generate(prompt, 700))

            # Show the topic briefly (e.g., ~1.2s) before generating the content
            QTimer.singleShot(1200, start_persona)

        # Wire worker for topic generation first
        try:
            worker.finished.disconnect()
        except Exception:
            pass
        try:
            worker.error.disconnect()
        except Exception:
            pass
        worker.finished.connect(on_topic_finished)
        worker.error.connect(on_error)

        topic_prompt = build_topic_prompt()
        QTimer.singleShot(0, lambda: worker.generate(topic_prompt, 50))

    QTimer.singleShot(0, run_one)
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
