import pickle
from dataclasses import asdict
from typing import List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .chunker import Chunk

SECURITY_SYNONYMS = {
    "brute force": "failed password invalid user attempt repeated",
    "bruteforce": "failed password invalid user attempt repeated",
    "port scan": "DROP DPT PROTO TCP kernel",
    "scanning": "DROP DPT PROTO TCP kernel",
    "sql injection": "OR 1 1 login POST admin",
    "sqli": "OR 1 1 login POST admin",
    "successful login": "Accepted password",
    "logged in": "Accepted password",
    "blocked": "DROP",
    "allowed": "ACCEPT",
    "unauthorized": "Failed 401 invalid",
}


def expand_query(query: str) -> str:
    """Append synonym terms for any recognized security phrase in the
    query. Purely additive - the original query text is always kept,
    so this only ever broadens recall, never rewrites intent."""
    expanded = query
    lowered = query.lower()
    for phrase, expansion in SECURITY_SYNONYMS.items():
        if phrase in lowered:
            expanded += " " + expansion
    return expanded


class VectorStore:
    def __init__(self):
        self.vectorizer: TfidfVectorizer = TfidfVectorizer(
            lowercase=True,
            token_pattern=r"(?u)\b\w[\w.\-@:/]*\b",  # keep IPs, paths, users intact
            ngram_range=(1, 2),
        )
        self.matrix = None
        self.chunks: List[Chunk] = []

    def build(self, chunks: List[Chunk]) -> None:
        self.chunks = chunks
        texts = [c.text for c in chunks]
        self.matrix = self.vectorizer.fit_transform(texts)

    def search(self, query: str, top_k: int = 6) -> List[Tuple[Chunk, float]]:
        if self.matrix is None or not self.chunks:
            return []
        q_vec = self.vectorizer.transform([expand_query(query)])
        sims = cosine_similarity(q_vec, self.matrix)[0]
        top_idx = np.argsort(sims)[::-1][:top_k]
        results = [(self.chunks[i], float(sims[i])) for i in top_idx if sims[i] > 0]
        return results

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "vectorizer": self.vectorizer,
                    "matrix": self.matrix,
                    "chunks": [asdict(c) for c in self.chunks],
                },
                f,
            )

    @classmethod
    def load(cls, path: str) -> "VectorStore":
        with open(path, "rb") as f:
            data = pickle.load(f)
        store = cls()
        store.vectorizer = data["vectorizer"]
        store.matrix = data["matrix"]
        store.chunks = [Chunk(**c) for c in data["chunks"]]
        return store
