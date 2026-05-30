import re
import os
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class LogEntry:
    source_file: str
    line_number: int
    raw_text: str
    log_type: str = "unknown"
    timestamp: Optional[str] = None
    fields: Dict[str, str] = field(default_factory=dict)

    @property
    def entry_id(self) -> str:
        return f"{os.path.basename(self.source_file)}:{self.line_number}"

    @property
    def entry_hash(self) -> str:
        """SHA-256 of the exact raw line. Used for integrity verification."""
        return hashlib.sha256(self.raw_text.encode("utf-8")).hexdigest()



SSH_FAILED_RE = re.compile(
    r"^(?P<ts>\w{3}\s+\d+\s[\d:]+)\s+\S+\s+sshd\[\d+\]:\s+Failed password for"
    r"(?: invalid user)? (?P<user>\S+) from (?P<ip>[\d.]+) port (?P<port>\d+)"
)
SSH_ACCEPTED_RE = re.compile(
    r"^(?P<ts>\w{3}\s+\d+\s[\d:]+)\s+\S+\s+sshd\[\d+\]:\s+Accepted password for"
    r" (?P<user>\S+) from (?P<ip>[\d.]+) port (?P<port>\d+)"
)
SSH_INVALID_USER_RE = re.compile(
    r"^(?P<ts>\w{3}\s+\d+\s[\d:]+)\s+\S+\s+sshd\[\d+\]:\s+Invalid user (?P<user>\S+)"
    r" from (?P<ip>[\d.]+)"
)
FIREWALL_RE = re.compile(
    r"^(?P<ts>\w{3}\s+\d+\s[\d:]+)\s+\S+\s+kernel:\s+\[.*?\]\s+(?P<action>\S+)\s+.*?"
    r"IN=(?P<in_if>\S*).*?SRC=(?P<src>[\d.]+)\s+DST=(?P<dst>[\d.]+).*?"
    r"PROTO=(?P<proto>\S+).*?DPT=(?P<dpt>\d+)"
)
WEB_RE = re.compile(
    r'^(?P<ip>[\d.]+)\s+\S+\s+\S+\s+\[(?P<ts>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+\S+"\s+(?P<status>\d+)\s+(?P<size>\S+)'
)


def _try_parsers(line: str) -> (str, Optional[str], Dict[str, str]):
    """Return (log_type, timestamp, fields) for a raw line."""
    m = SSH_FAILED_RE.match(line)
    if m:
        return "ssh_failed_login", m.group("ts"), m.groupdict()

    m = SSH_ACCEPTED_RE.match(line)
    if m:
        return "ssh_accepted_login", m.group("ts"), m.groupdict()

    m = SSH_INVALID_USER_RE.match(line)
    if m:
        return "ssh_invalid_user", m.group("ts"), m.groupdict()

    m = FIREWALL_RE.match(line)
    if m:
        return "firewall_event", m.group("ts"), m.groupdict()

    m = WEB_RE.match(line)
    if m:
        return "web_access", m.group("ts"), m.groupdict()

    return "unknown", None, {}


def parse_line(line: str, source_file: str, line_number: int) -> Optional[LogEntry]:
    line = line.rstrip("\n")
    if not line.strip():
        return None
    log_type, ts, fields = _try_parsers(line)
    return LogEntry(
        source_file=source_file,
        line_number=line_number,
        raw_text=line,
        log_type=log_type,
        timestamp=ts,
        fields=fields,
    )


def parse_file(path: str) -> List[LogEntry]:
    entries = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, start=1):
            entry = parse_line(line, path, i)
            if entry:
                entries.append(entry)
    return entries


def parse_directory(dir_path: str) -> List[LogEntry]:
    """Recursively parse every file under dir_path. Recursive so that
    zip bundles extracted with nested folders (e.g. logs/2026-08-20/*.log)
    are fully picked up, not just top-level files."""
    entries: List[LogEntry] = []
    for root, _dirs, files in os.walk(dir_path):
        for fname in sorted(files):
            if fname.startswith("."):
                continue
            if fname.lower().endswith(".zip"):
                continue  # leftover archives are skipped, not parsed as text
            full = os.path.join(root, fname)
            entries.extend(parse_file(full))
    entries.sort(key=lambda e: (e.source_file, e.line_number))
    return entries
