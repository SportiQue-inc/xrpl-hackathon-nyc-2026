"""Mask secrets before anything is logged or shown. Transaction hashes and addresses stay readable."""
from __future__ import annotations

import logging
import re

_PATTERNS = [
    (re.compile(r"\bs[1-9A-HJ-NP-Za-km-z]{28,30}\b"), "s***seed***"),            # XRPL family seed
    (re.compile(r"\bsEd[1-9A-HJ-NP-Za-km-z]{27,29}\b"), "s***seed***"),          # ed25519 seed
    (re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{16,}\b"), "sk-***"),          # LLM API keys
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), "***jwt***"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"), r"\1***"),
    (re.compile(r"(?i)\b(private_key|secret|seed|key_hex|fulfillment)(\"?\s*[:=]\s*\"?)[A-Fa-f0-9]{32,}"),
     r"\1\2***"),
]


def mask(text: str) -> str:
    if not text:
        return text
    for rx, rep in _PATTERNS:
        text = rx.sub(rep, text)
    return text


class MaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask(str(record.msg))
        if record.args:
            record.args = tuple(mask(str(a)) for a in record.args)
        return True


def install_logging_filter():
    f = MaskingFilter()
    for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error", "agentrail"):
        lg = logging.getLogger(name)
        if not any(isinstance(x, MaskingFilter) for x in lg.filters):
            lg.addFilter(f)
