import os
from typing import List, Tuple, Dict, Any

from .vector_store import VectorStore
from .chunker import Chunk
from .verifier import verify_answer, VerificationReport

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


class RAGEngine:
    def __init__(self, store: VectorStore, model: str = "gemini-3.6-flash", top_k: int = 6):
        self.store = store
        self.model = model
        self.top_k = top_k
        self._client = None

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

    def answer(self, question: str) -> Dict[str, Any]:
        retrieved = self.store.search(question, top_k=self.top_k)
        if not retrieved:
            return {
                "question": question,
                "answer": "No relevant log evidence was found in the index for this question.",
                "sources": [],
                "verification": None,
            }

        prompt = build_prompt(question, retrieved)
        client = self._get_client()

        from google.genai import types
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=800,
            ),
        )
        answer_text = response.text

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
