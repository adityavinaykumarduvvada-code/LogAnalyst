import os
import time
import logging
from typing import List, Tuple, Dict, Any, Optional, Sequence, Union

from .vector_store import VectorStore
from .chunker import Chunk
from .verifier import verify_answer, VerificationReport

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a security log analyst assistant. You will be given a
user question and a numbered list of log-evidence excerpts retrieved from an
index of real log files.

Rules you MUST follow:
1. Only use information present in the numbered sources below. Do not use
   outside knowledge about IPs, users, or systems.
2. Every factual claim you make must end with a citation like [2] pointing to
   the source number that supports it. If a claim draws on multiple sources,
   cite all of them, e.g. [1][3].
3. If the sources do not contain enough evidence to answer, say so plainly
   instead of guessing.
4. Be concise and analytical: state what happened, when, from where, and how
   confident you are, based only on the cited evidence.
"""

# Tried in order. The first model that responds wins.
# Override without touching code via:  GEMINI_MODELS=gemini-3.7-flash,gemini-3.6-flash
DEFAULT_MODELS: List[str] = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]

# HTTP codes that mean "this model is busy/unavailable right now -> try the next one".
#   429 = rate limited / quota exhausted, 500/502/503/504 = overloaded or server error,
#   404 = model name not found (retired or not enabled for your key).
FALLBACK_STATUS_CODES = {404, 429, 500, 502, 503, 504}


class AllModelsFailedError(RuntimeError):
    """Raised when every model in the fallback chain failed."""

    def __init__(self, errors: Dict[str, str]):
        self.errors = errors
        detail = "; ".join(f"{m}: {e}" for m, e in errors.items())
        super().__init__(f"All Gemini models failed. {detail}")


def build_prompt(question: str, retrieved: List[Tuple[Chunk, float]]) -> str:
    lines = [f"Question: {question}", "", "Sources:"]
    for i, (chunk, score) in enumerate(retrieved, start=1):
        lines.append(
            f"[{i}] (file={os.path.basename(chunk.source_file)}, "
            f"lines={chunk.line_start}-{chunk.line_end}, "
            f"type={','.join(chunk.log_types)}, relevance={score:.2f})\n"
            f"{chunk.text}"
        )
    lines.append("")
    lines.append("Answer the question using only the sources above, with citations.")
    return "\n".join(lines)


def _models_from_env() -> Optional[List[str]]:
    raw = os.environ.get("GEMINI_MODELS", "").strip()
    if not raw:
        return None
    return [m.strip() for m in raw.split(",") if m.strip()]


class RAGEngine:
    def __init__(
        self,
        store: VectorStore,
        model: Union[str, Sequence[str], None] = None,
        top_k: int = 6,
        retries_per_model: int = 1,
        retry_backoff: float = 1.5,
        cooldown_seconds: float = 60.0,
    ):
        """
        model: a single model name, a list of models to try in order, or None to use
               GEMINI_MODELS from the environment (falling back to DEFAULT_MODELS).
        retries_per_model: extra attempts on the same model before moving on
               (0 = jump to the next model immediately).
        retry_backoff: seconds to wait before a retry on the same model (doubles each try).
        cooldown_seconds: after a model fails, skip it for this long on later
               requests so you don't waste time hammering an overloaded model.
        """
        self.store = store
        if model is None:
            self.models = _models_from_env() or list(DEFAULT_MODELS)
        elif isinstance(model, str):
            # Keep the requested model first, then fall back to the defaults.
            self.models = [model] + [m for m in DEFAULT_MODELS if m != model]
        else:
            self.models = list(model)
        if not self.models:
            raise ValueError("At least one Gemini model must be configured.")

        self.top_k = top_k
        self.retries_per_model = max(0, retries_per_model)
        self.retry_backoff = retry_backoff
        self.cooldown_seconds = cooldown_seconds
        self._cooldown_until: Dict[str, float] = {}
        self._client = None

    # Kept for backwards compatibility with code that reads engine.model
    @property
    def model(self) -> str:
        return self.models[0]

    def _get_client(self):
        if self._client is None:
            from google import genai
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. Copy .env.example to .env "
                    "and add your key, or export it in your shell."
                )
            self._client = genai.Client(api_key=api_key)
        return self._client

    def _ordered_models(self) -> List[str]:
        """Models not in cooldown first (in configured order), cooled-down ones last."""
        now = time.monotonic()
        ready = [m for m in self.models if self._cooldown_until.get(m, 0) <= now]
        cooling = [m for m in self.models if self._cooldown_until.get(m, 0) > now]
        return ready + cooling

    def _generate_with_fallback(self, prompt: str) -> Tuple[str, str, List[Dict[str, str]]]:
        """Returns (answer_text, model_used, attempts_log)."""
        from google.genai import types, errors

        client = self._get_client()
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=800,
        )

        failures: Dict[str, str] = {}
        attempts: List[Dict[str, str]] = []

        for model in self._ordered_models():
            for attempt in range(self.retries_per_model + 1):
                try:
                    response = client.models.generate_content(
                        model=model, contents=prompt, config=config
                    )
                    text = response.text
                    if not text or not text.strip():
                        # Empty/blocked output: treat as a soft failure and try another model.
                        raise ValueError("empty response")
                    self._cooldown_until.pop(model, None)
                    attempts.append({"model": model, "status": "ok"})
                    return text, model, attempts

                except errors.APIError as e:
                    code = getattr(e, "code", None)
                    msg = f"HTTP {code}: {getattr(e, 'message', e)}"
                    attempts.append({"model": model, "status": msg})
                    if code not in FALLBACK_STATUS_CODES:
                        # 400/401/403 etc. are problems with the request or key —
                        # switching models won't fix them, so fail loudly.
                        raise
                    failures[model] = msg
                    logger.warning("Gemini model %s failed (%s)", model, msg)
                    if code == 404:
                        break  # model doesn't exist; retrying the same name is pointless
                except ValueError as e:
                    msg = str(e)
                    attempts.append({"model": model, "status": msg})
                    failures[model] = msg
                    logger.warning("Gemini model %s returned no text", model)
                    break

                if attempt < self.retries_per_model:
                    time.sleep(self.retry_backoff * (2 ** attempt))

            # Every attempt on this model failed: park it for a while.
            self._cooldown_until[model] = time.monotonic() + self.cooldown_seconds

        raise AllModelsFailedError(failures)

    def answer(self, question: str) -> Dict[str, Any]:
        retrieved = self.store.search(question, top_k=self.top_k)
        if not retrieved:
            return {
                "question": question,
                "answer": "No relevant log evidence was found in the index for this question.",
                "sources": [],
                "verification": None,
                "model_used": None,
            }

        prompt = build_prompt(question, retrieved)
        answer_text, model_used, attempts = self._generate_with_fallback(prompt)

        report: VerificationReport = verify_answer(answer_text, retrieved)

        sources = [
            {
                "index": i + 1,
                "chunk_id": chunk.chunk_id,
                "source_file": os.path.basename(chunk.source_file),
                "lines": [chunk.line_start, chunk.line_end],
                "log_types": chunk.log_types,
                "relevance": round(score, 3),
                "hash": chunk.chunk_hash,
                "text": chunk.text,
            }
            for i, (chunk, score) in enumerate(retrieved)
        ]

        return {
            "question": question,
            "answer": answer_text,
            "model_used": model_used,
            "model_attempts": attempts,
            "sources": sources,
            "verification": {
                "trust_score": report.trust_score,
                "valid_citations": report.valid_citations,
                "invalid_citations": report.invalid_citations,
                "integrity_ok": report.integrity_ok,
                "integrity_mismatches": report.integrity_mismatches,
                "unsupported_claims": report.unsupported_claims,
            },
        }
