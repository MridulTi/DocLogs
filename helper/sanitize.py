from __future__ import annotations
from dataclasses import dataclass
import re

from helper.entry import DailyEntry

@dataclass
class RedactionFinding:
    kind: str
    matched: str

@dataclass
class FlagFinding:
    kind: str
    matched: str



# (name, regex pattern)
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("internal_url", re.compile(r"https?://[^\s]*\.(?:internal|corp|local)[^\s]*", re.I)),
    ("private_ip", re.compile(r"\b(?:10|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b")),
    ("api_key", re.compile(r"\b(?:sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b", re.I)),
]
PLACEHOLDERS = {
    "internal_url": "[REDACTED:internal_url]",
    "private_ip": "[REDACTED:private_ip]",
    "api_key": "[REDACTED:api_key]",
    "bearer_token": "[REDACTED:token]",
}

FLAG_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("password_assignment", re.compile(r"(?i)(password|passwd|secret|token)\s*[:=]\s*\S+")),
    ("aws_account", re.compile(r"\b\d{12}\b")),  # 12-digit AWS account IDs
]


def redact(text:str)-> tuple(str, list[RedactionFinding]):
    finding: list[RedactionFinding] = []
    result = text

    for (kind,pattern) in PATTERNS:
        for match in pattern.findall(result):
            finding.append(RedactionFinding(kind=kind, matched=match))
            placeholder = PLACEHOLDERS.get(kind, "[REDACTED]")
            result = result.replace(match,placeholder)
    return result, finding


def text_from_entry(entry: DailyEntry) -> str:
    parts: list[str] = []
    if entry.notes:
        parts.append(entry.notes)
    for commit in entry.commits:
        parts.append(commit.subject)
    return "\n".join(parts)


def sanitize_entry(entry: DailyEntry) -> tuple[str, list[RedactionFinding]]:
    return redact(text_from_entry(entry))

def scan_flags(text:str) -> list[FlagFinding]:
    flags:list[FlagFinding] = []
    seen: set[str] = set()

    for kind, pattern in FLAG_PATTERNS:
        for match in pattern.findall(text):
            matched = match if isinstance(match, str) else match[0]
            key = matched.lower()
            if key not in seen:
                seen.add(key)
                flags.append(FlagFinding(kind=kind, matched=matched))
    return flags


def sanitize_with_review(text: str) -> tuple(str, list[RedactionFinding], list[FlagFinding]):
    sanitized, findings = redact(text)
    flags = scan_flags(text)
    return sanitized, findings, flags
