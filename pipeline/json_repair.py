#!/usr/bin/env python3
"""
json_repair.py — JSON repair strategies adapted from OutputGuard for Maxwell's Gemma-4 pipeline.

Gemma-4 via OMLX with response_format="json_object" produces mostly valid JSON,
but these failure modes still occur:
  1. Trailing commas before } or ] (LLM habit)
  2. Python booleans/None (True/False/None → true/false/null)
  3. Truncated JSON from token limits (missing closers)
  4. Unquoted object keys
  5. NaN/Infinity/undefined values
  6. ... ellipsis placeholders
  7. JS-style comments (// and /* */)
  8. Stray tokens corrupting individual objects in arrays (position-preserving salvage)

Strategies NOT needed for Gemma-4 (omitted to avoid bloat):
  - fix_encoding (GPT-2 BPE artifacts — Gemma uses SentencePiece)
  - fix_newlines (response_format="json_object" handles this)
  - fix_quotes (Gemma-4 doesn't emit single-quoted JSON)
  - fix_inner_quotes (same reason)
  - fix_unicode (Gemma-4 handles Unicode correctly)

Based on OutputGuard (MIT) by ndcorder — strategies adapted for Maxwell pipeline.
"""

import re
import json

# ── Strategy 1: Strip markdown fences ──

_FENCE_RE = re.compile(r"```[a-zA-Z]*\s*\n(.*?)\n\s*```", re.DOTALL)
_UNCLOSED_FENCE_RE = re.compile(r"```[a-zA-Z]*\s*\n(.*)", re.DOTALL)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```)."""
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    m = _UNCLOSED_FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    return text


# ── Strategy 2: Remove comments ──

def _remove_comments(text: str) -> str:
    """Strip JS-style // and /* */ comments, preserving strings."""
    result = []
    i, n = 0, len(text)
    in_string = False

    while i < n:
        ch = text[i]
        if in_string:
            result.append(ch)
            if ch == "\\" and i + 1 < n:
                result.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        result.append(ch)
        i += 1
    return "".join(result)


# ── Strategy 3: Fix Python booleans/None ──

_BOOL_PATTERNS = [
    (re.compile(r"\bTrue\b"), "true"),
    (re.compile(r"\bFalse\b"), "false"),
    (re.compile(r"\bNone\b"), "null"),
]


def _fix_booleans(text: str) -> str:
    """Replace Python True/False/None with JSON equivalents (outside strings)."""
    for pattern, replacement in _BOOL_PATTERNS:
        matches = list(pattern.finditer(text))
        for m in reversed(matches):
            before = text[: m.start()]
            # Count unescaped quotes: even count → outside string
            if (before.count('"') - before.count('\\"')) % 2 == 0:
                text = text[: m.start()] + replacement + text[m.end() :]
    return text


# ── Strategy 4: Fix trailing commas ──

_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def _fix_commas(text: str) -> str:
    """Remove trailing commas before } and ]."""
    return _TRAILING_COMMA_RE.sub(r"\1", text)


# ── Strategy 5: Fix unquoted keys ──

_UNQUOTED_KEY_RE = re.compile(r"([{,]\s*)([a-zA-Z_$][a-zA-Z0-9_.$-]*)\s*:")


def _fix_keys(text: str) -> str:
    """Add double quotes to unquoted object keys (outside strings)."""
    result = []
    i, n = 0, len(text)
    while i < n:
        if text[i] == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            result.append(text[i:j])
            i = j
        else:
            j = text.find('"', i)
            if j == -1:
                j = n
            segment = text[i:j]
            segment = _UNQUOTED_KEY_RE.sub(r'\1"\2":', segment)
            result.append(segment)
            i = j
    return "".join(result)


# ── Strategy 6: Fix NaN/Infinity/undefined ──

_VALUE_PATTERNS = [
    (re.compile(r"-Infinity"), "null"),
    (re.compile(r"\bInfinity\b"), "null"),
    (re.compile(r"\bNaN\b"), "null"),
    (re.compile(r"\bundefined\b"), "null"),
]


def _fix_values(text: str) -> str:
    """Replace NaN, Infinity, undefined with null (outside strings)."""
    for pattern, replacement in _VALUE_PATTERNS:
        matches = list(pattern.finditer(text))
        for m in reversed(matches):
            before = text[: m.start()]
            if (before.count('"') - before.count('\\"')) % 2 == 0:
                text = text[: m.start()] + replacement + text[m.end() :]
    return text


# ── Strategy 7: Fix ellipsis placeholders ──

def _fix_ellipsis(text: str) -> str:
    """Replace ... placeholders with valid JSON (null or empty container)."""
    try:
        result = []
        i, n = 0, len(text)
        in_string = False

        while i < n:
            ch = text[i]
            if in_string:
                result.append(ch)
                if ch == "\\" and i + 1 < n:
                    result.append(text[i + 1])
                    i += 2
                    continue
                if ch == '"':
                    in_string = False
                i += 1
                continue
            if ch == '"':
                in_string = True
                result.append(ch)
                i += 1
                continue
            if ch == "/" and i + 1 < n and text[i + 1] == "/":
                while i < n and text[i] != "\n":
                    i += 1
                continue
            if ch == "/" and i + 1 < n and text[i + 1] == "*":
                i += 2
                while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i += 2
                continue
            if ch == "." and i + 2 < n and text[i + 1] == "." and text[i + 2] == ".":
                before = "".join(result).rstrip()
                after_idx = i + 3
                while after_idx < n and text[after_idx] in " \t\r\n":
                    after_idx += 1
                after_ch = text[after_idx] if after_idx < n else ""
                if before.endswith("[") and after_ch == "]":
                    i += 3; continue  # [...] → []
                elif before.endswith("{") and after_ch == "}":
                    i += 3; continue  # {...} → {}
                elif before.endswith(",") and after_ch in "],":
                    joined = "".join(result)
                    stripped = joined.rstrip()
                    if stripped.endswith(","):
                        result.clear()
                        result.append(stripped[:-1])
                    i += 3; continue
                else:
                    result.append("null")
                    i += 3; continue
            result.append(ch)
            i += 1

        output = "".join(result)
        output = re.sub(r",\s*([\]\}])", r"\1", output)
        return output
    except Exception:
        return text


# ── Strategy 8: Balance missing closers ──

_MATCH = {"{": "}", "[": "]"}


def _fix_closers(text: str) -> str:
    """Append missing closing braces/brackets for unmatched openers."""
    stack = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False; continue
        if ch == "\\" and in_string:
            escape = True; continue
        if ch == '"':
            in_string = not in_string; continue
        if in_string:
            continue
        if ch in "{[":
            stack.append(ch)
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()
    if not stack:
        return text
    return text + "".join(_MATCH[o] for o in reversed(stack))


# ── Strategy 9: Fix truncated JSON ──

def _fix_truncated(text: str) -> str:
    """Recover truncated JSON from token-limit cutoffs."""
    try:
        stripped = text.rstrip()
        if not stripped or stripped[0] not in "{[":
            return text

        # Count unescaped quotes
        quote_count = 0
        i = 0
        while i < len(stripped):
            if stripped[i] == "\\":
                i += 2; continue
            if stripped[i] == '"':
                quote_count += 1
            i += 1

        working = stripped
        if quote_count % 2 != 0:
            working += '"'

        # Remove trailing structural problems
        changed = True
        while changed:
            changed = False
            w = working.rstrip()
            if w.endswith(","):
                working = w[:-1]; changed = True; continue
            if w.endswith(":"):
                working = w + " null"; changed = True; continue

        # Remove dangling partial key
        m = re.search(r',\s*"[^"]*"\s*$', working.rstrip())
        if m:
            after_comma = working[m.start() + 1:].strip()
            if re.fullmatch(r'"[^"]*"', after_comma):
                working = working[: m.start()]

        working = _fix_closers(working)
        return working
    except Exception:
        return text


# ── Strategy 10: Position-preserving array salvage (Maxwell's existing approach) ──

def _salvage_array_objects(text: str) -> list:
    """Split a JSON array on object boundaries when the whole array won't parse.
    
    Preserves position and count by splitting on `},{` between top-level objects.
    Each piece is parsed individually; corrupted pieces become None.
    None placeholders keep index alignment for downstream s3a_meta merge.
    """
    l, r = text.find("["), text.rfind("]")
    body = (text[l + 1: r] if (l != -1 and r != -1 and r > l) else text).strip()
    if "{" not in body:
        return []
    
    pieces = re.split(r"\}\s*,\s*\{", body)
    out = []
    for piece in pieces:
        blk = piece.strip()
        if not blk.startswith("{"):
            blk = "{" + blk
        if not blk.endswith("}"):
            blk = blk + "}"
        try:
            out.append(json.loads(blk))
        except json.JSONDecodeError:
            out.append(None)
    return out


# ── Pipeline: apply all repairs in order ──

def repair_json(text: str) -> str:
    """Apply all JSON repair strategies to a potentially malformed JSON string.
    
    Strategies are applied in order from least-destructive to most-destructive.
    Returns the repaired text (may still not parse if unfixable).
    """
    # Phase 1: Cleanup (non-structural)
    text = _strip_fences(text)
    # Phase 2: Remove non-JSON artifacts
    text = _remove_comments(text)
    # Phase 3: Fix value-level issues
    text = _fix_booleans(text)
    text = _fix_values(text)
    text = _fix_ellipsis(text)
    # Phase 4: Fix structural issues
    text = _fix_keys(text)
    text = _fix_commas(text)
    # Phase 5: Fix truncation (must be last — adds closers)
    text = _fix_truncated(text)
    return text


def parse_json_robust(text: str) -> dict | list:
    """Parse JSON with full repair pipeline. Returns parsed object, salvaged list, or empty list."""
    # Phase 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Phase 2: Repair + parse
    repaired = repair_json(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    
    # Phase 3: Array salvage on repaired text
    result = _salvage_array_objects(repaired)
    if result and any(isinstance(r, dict) for r in result):
        return result
    
    # Phase 4: Array salvage on original (for cases where repair made things worse)
    result = _salvage_array_objects(text)
    if result and any(isinstance(r, dict) for r in result):
        return result
    
    return []
