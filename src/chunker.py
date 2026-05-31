import hashlib
from dataclasses import dataclass, field
from typing import List, Dict
from .log_parser import LogEntry


@dataclass
class Chunk:
    chunk_id: str
    text: str
    source_file: str
    line_start: int
    line_end: int
    log_types: List[str]
    entry_hashes: List[str] = field(default_factory=list)

    @property
    def chunk_hash(self) -> str:
        """Hash of the exact chunk text - recomputed at query time to
        verify the chunk has not been tampered with since ingestion."""
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def chunk_entries(entries: List[LogEntry], strategy: str = "line") -> List[Chunk]:
    if strategy == "line":
        return _chunk_by_line(entries)
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")


def _chunk_by_line(entries: List[LogEntry]) -> List[Chunk]:
    chunks = []
    for e in entries:
        cid = f"{e.entry_id}"
        chunks.append(
            Chunk(
                chunk_id=cid,
                text=e.raw_text,
                source_file=e.source_file,
                line_start=e.line_number,
                line_end=e.line_number,
                log_types=[e.log_type],
                entry_hashes=[e.entry_hash],
            )
        )
    return chunks

