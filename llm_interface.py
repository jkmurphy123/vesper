# llm_interface.py
from __future__ import annotations
import os
from typing import Optional

try:
    from llama_cpp import Llama  # type: ignore
except Exception as e:  # pragma: no cover
    Llama = None  # defer import errors until used


class LLMInterface:
    """Thin wrapper around llama-cpp-python for simple text generation.

    For Phase 1 we do a single non-streaming call with a test prompt.
    In later phases, we can add streaming, function-calling, or chat templates.
    """

    def __init__(
        self,
        model_path: str,
        n_gpu_layers: int = -1,
        n_ctx: int = 4096,
        n_threads: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.95,
    ) -> None:
        if Llama is None:
            raise RuntimeError(
                "llama_cpp not available. Install llama-cpp-python built for Jetson.")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        self.temperature = temperature
        self.top_p = top_p

        # On Jetson Orin Nano with CUDA build, set n_gpu_layers=-1 to place all on GPU if memory allows.
        # Adjust if you see OOMs.
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,  # None -> library default
            n_gpu_layers=n_gpu_layers,
            verbose=False,
        )

    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        """Simple text completion.

        If your model expects chat format, wrap the prompt accordingly (later phases).
        """
        result = self.llm(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            stop=None,
        )
        # llama-cpp returns a dict; text is under 'choices'[0]['text'] for completion API
        return result["choices"][0]["text"].strip()