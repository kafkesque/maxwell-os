"""
omlx_call.py — Inference wrapper with OMLX + direct MLX backends.
==================================================================
Authority: CONSTITUTION.md C1, C8, C9, C21 (Swappable Infrastructure)

Features:
  - temp=0.0 ENFORCED on every call (R7)
  - Two backends: OMLX (HTTP) and MLX (direct, speculative decoding)
  - Auto JSON repair on output
  - Timeout handling + retry (OMLX), eager loading (MLX)
  - Dispatch controlled by MAXWELL_INFERENCE_BACKEND env var or config

Usage:
    from pipeline.omlx_call import call_omlx, call_omlx_json

    text = call_omlx("Extract principles from: ...", model="Qwen3.6-35B-A3B-4bit")
    data = call_omlx_json("Return JSON: {...}", model="Qwen3.6-35B-A3B-4bit")

Backend selection:
    MAXWELL_INFERENCE_BACKEND=mlx   → direct MLX with speculative decoding
    MAXWELL_INFERENCE_BACKEND=omlx  → OMLX HTTP server (default)

Generator ≠ Verifier (R5): Use Qwen3.6 for generation, Phi-4-mini for verification.
"""

import json
import os as _os
import threading
import time

import requests

from pipeline.json_repair import parse_json_robust, repair_json
from pipeline.pipeline_paths import (
    GEN_MAX_TOKENS,
    GEN_MODEL,
    GEN_TEMPERATURE,
    OMLX_API_KEY,
    OMLX_CB_COOLDOWN_SECONDS,
    OMLX_CB_ENABLED,
    OMLX_CB_FAILURE_THRESHOLD,
    OMLX_DEFAULT_TIMEOUT,
    OMLX_MAX_RETRIES,
    OMLX_RETRY_DELAY,
    OMLX_URL,
    VERIFY_MODEL,
)

# ── Constants (T0.2: de-hardcoded — sourced from pipeline_config.yaml) ────
DEFAULT_TIMEOUT: int = OMLX_DEFAULT_TIMEOUT     # seconds (from config)
MAX_RETRIES: int = OMLX_MAX_RETRIES             # (from config)
RETRY_DELAY: int = OMLX_RETRY_DELAY             # seconds (from config)

# temp=0.0 — NEVER override (R7)
TEMPERATURE: float = GEN_TEMPERATURE            # 0.0 from config

CHAT_ENDPOINT = f"{OMLX_URL}/v1/chat/completions"


# ── Circuit breaker (D2187, P1-3) ────────────────────────────────────────
class CircuitBreaker:
    """Fail-fast guard for OMLX HTTP calls.

    States:
      CLOSED    — normal operation (calls allowed, failures counted)
      OPEN      — threshold exceeded; calls refused for cooldown window
      HALF_OPEN — cooldown elapsed; exactly one probe call allowed

    A single success resets to CLOSED. A probe failure re-opens.
    Prevents hammering a dead OMLX server for the duration of a long
    Stage 2 run (~1,100 extraction calls).
    """

    def __init__(self, failure_threshold: int, cooldown_seconds: float) -> None:
        self._threshold: int = max(1, failure_threshold)
        self._cooldown: float = max(1.0, cooldown_seconds)
        self._consecutive_failures: int = 0
        self._open_until: float = 0.0
        self._state: str = "CLOSED"
        self._lock: threading.Lock = threading.Lock()  # D2211: thread safety for ThreadPoolExecutor

    @property
    def state(self) -> str:
        """Current breaker state: CLOSED | OPEN | HALF_OPEN."""
        if self._state == "OPEN" and time.time() >= self._open_until:
            self._state = "HALF_OPEN"
        return self._state

    def allow_request(self) -> bool:
        """True if a request may proceed; False = fast-fail (breaker OPEN)."""
        with self._lock:
            return self.state != "OPEN"

    def record_success(self) -> None:
        """Successful call — reset failure count, close breaker."""
        with self._lock:
            self._consecutive_failures = 0
            self._state = "CLOSED"

    def record_failure(self) -> None:
        """Failed call — count toward threshold; trip breaker when reached."""
        with self._lock:
            self._consecutive_failures += 1
            if self._state == "HALF_OPEN":
                # Canonical: probe failure re-opens immediately (no repeated probes)
                self._state = "OPEN"
                self._open_until = time.time() + self._cooldown
            elif self._consecutive_failures >= self._threshold:
                self._state = "OPEN"
                self._open_until = time.time() + self._cooldown


# Module-level singleton (process-wide state survives across calls)
_breaker = CircuitBreaker(max(OMLX_CB_FAILURE_THRESHOLD, 25), OMLX_CB_COOLDOWN_SECONDS)


class CircuitOpenError(RuntimeError):
    """Raised when the OMLX circuit breaker is OPEN (fast-fail)."""

# ── Backend selection ─────────────────────────────────────────────────────
_INFERENCE_BACKEND = _os.environ.get("MAXWELL_INFERENCE_BACKEND", "omlx")

# ── MLX backend (lazy-loaded) ─────────────────────────────────────────────
_mlx_providers: dict[str, object] = {}  # model_name → MLXInferenceProvider

# Draft model pairings for speculative decoding (1.5-2× speedup)
# D2176: Qwen3.x models CANNOT use Qwen2.5 draft models — speculative decoding
# requires byte-for-byte tokenizer parity. Qwen2.5 and Qwen3 have different
# tokenizers. Using mismatched draft/target pairs causes 99% draft rejection
# (destroying the speedup) and risks incoherent token generation.
# Fix: disable speculative decoding for Qwen3.x until Qwen3 draft models exist.
# For models where a same-family draft IS available, the mapping remains.
_MLX_DRAFT_MODELS: dict[str, str] = {
    # Qwen3.x — NO compatible draft model yet (Qwen2.5 has different tokenizer)
    # "Qwen3.6-35B-A3B-4bit": "mlx-community/Qwen2.5-0.5B-Instruct-4bit",  # DISABLED D2176
    # "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit": "mlx-community/Qwen2.5-0.5B-Instruct-4bit",  # DISABLED D2176
    "gemma-4-E4B-it-MLX-4bit": "mlx-community/gemma-2-2b-it-4bit",
}

# Short name → HF path mapping (add mlx-community/ prefix if not present)
def _mlx_model_path(model_name: str) -> str:
    """Map short OMLX model names to MLX paths.

    D2208: Check local OMLX model directory first (~/.omlx/models/)
    before falling back to HuggingFace Hub. OMLX stores models locally
    and HF downloads fail without internet or token.
    """
    import os as _os
    if model_name.startswith("mlx-community/"):
        return model_name

    # Check local OMLX model directory first
    local_base = _os.path.expanduser("~/.omlx/models")
    local_path = _os.path.join(local_base, model_name)
    if _os.path.isdir(local_path) and _os.path.isfile(_os.path.join(local_path, "config.json")):
        return local_path

    # Try alternative local paths (some models use different naming)
    if _os.path.isdir(local_base):
        for entry in _os.listdir(local_base):
            entry_path = _os.path.join(local_base, entry)
            if _os.path.isdir(entry_path) and model_name in entry:
                if _os.path.isfile(_os.path.join(entry_path, "config.json")):
                    return entry_path

    # Fallback: HF Hub
    return f"mlx-community/{model_name}"


def _get_mlx_provider(model_name: str):
    """Get or create MLX provider for a model (with draft model for speed)."""
    if model_name not in _mlx_providers:
        from pipeline.providers.mlx_provider import MLXInferenceProvider

        mlx_path = _mlx_model_path(model_name)
        draft_path = _MLX_DRAFT_MODELS.get(model_name)

        _mlx_providers[model_name] = MLXInferenceProvider(
            model_name=mlx_path,
            draft_model_name=draft_path,
        )
    return _mlx_providers[model_name]


def _call_mlx(prompt: str, model: str, system: str = "", max_tokens: int = 2048) -> str:
    """Direct MLX inference (no HTTP, speculative decoding)."""
    provider = _get_mlx_provider(model)
    result = provider.generate(
        prompt=prompt,
        system=system,
        max_tokens=max_tokens,
        temperature=0.0,
    )
    return result.text.strip()


def _call_mlx_json(prompt: str, model: str, system: str = "", max_tokens: int = 2048) -> dict:
    """Direct MLX JSON inference with auto-repair.

    D2178: Removed repair_fn= kwarg — parse_json_robust does not accept it.
    Instead, call repair_json as a pre-processing step before parsing.
    """
    raw = _call_mlx(prompt, model, system, max_tokens)
    try:
        return parse_json_robust(raw)
    except (json.JSONDecodeError, ValueError):
        # Fallback: repair then parse
        repaired = repair_json(raw)
        return json.loads(repaired)


def call_omlx(
    prompt: str,
    model: str = GEN_MODEL,
    system: str | None = None,
    max_tokens: int = GEN_MAX_TOKENS,
    timeout: int = DEFAULT_TIMEOUT,
    response_format: dict | None = None,
) -> str:
    """Call inference backend (OMLX HTTP or MLX direct) and return text.

    Dispatch is controlled by MAXWELL_INFERENCE_BACKEND env var:
      - 'mlx'  → direct MLX with speculative decoding (1.5-2× faster)
      - 'omlx' → OMLX HTTP server (default)

    Args:
        prompt: The user prompt.
        model: Model name (default: Qwen3.6-35B-A3B-4bit).
        system: Optional system message.
        max_tokens: Max tokens to generate.
        timeout: Request timeout in seconds (OMLX only).

    Returns:
        Generated text string.

    Raises:
        RuntimeError: After MAX_RETRIES failed attempts.
    """
    if _INFERENCE_BACKEND == "mlx":
        return _call_mlx(prompt, model, system or "", max_tokens)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {OMLX_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": max_tokens,
    }
    if response_format is not None:
        payload["response_format"] = response_format

    last_error = None
    # D2187: Circuit breaker fast-fail (skip retry loop when OPEN)
    if OMLX_CB_ENABLED and not _breaker.allow_request():
        raise CircuitOpenError(
            f"OMLX circuit breaker {_breaker.state} — "
            f"{_breaker._threshold} consecutive failures; "
            f"cooldown until {_breaker._open_until:.0f} (epoch s). "
            f"Check OMLX at {OMLX_URL}."
        )
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                CHAT_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            if OMLX_CB_ENABLED:
                _breaker.record_success()
            return content.strip()
        except requests.exceptions.Timeout:
            last_error = f"Timeout after {timeout}s"
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
        except requests.exceptions.ConnectionError:
            last_error = f"Connection refused at {OMLX_URL}"
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            if attempt < MAX_RETRIES and e.response.status_code >= 500:
                time.sleep(RETRY_DELAY * attempt)
            else:
                break  # Don't retry 4xx errors
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    if OMLX_CB_ENABLED:
        # D2211: 4xx = client error (OMLX healthy, request rejected). Don't trip breaker.
        # TODO(v3.1): Replace with FailureKind enum from pipeline/result_types.py
        if last_error and not str(last_error).startswith("HTTP 4"):
            _breaker.record_failure()
    raise RuntimeError(f"OMLX call failed after {MAX_RETRIES} attempts: {last_error}")


def call_omlx_json(
    prompt: str,
    model: str = GEN_MODEL,
    system: str | None = None,
    max_tokens: int = GEN_MAX_TOKENS,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict | list:
    """Call inference backend and parse the response as JSON.

    Dispatch is controlled by MAXWELL_INFERENCE_BACKEND env var.
    Uses json_repair.py to fix common LLM JSON errors before parsing.

    Args:
        prompt: The user prompt (should instruct the model to return JSON).
        model: Model name.
        system: Optional system message.
        max_tokens: Max tokens.
        timeout: Request timeout (OMLX only).

    Returns:
        Parsed JSON (dict or list).

    Raises:
        ValueError: If the response cannot be parsed as JSON.
    """
    if _INFERENCE_BACKEND == "mlx":
        return _call_mlx_json(prompt, model, system or "", max_tokens)
    # If no system message, add a JSON instruction
    if system is None:
        system = "You are a precise JSON generator. Return ONLY valid JSON. No markdown, no explanation."

    raw = call_omlx(
        prompt=prompt,
        model=model,
        system=system,
        max_tokens=max_tokens,
        timeout=timeout,
        response_format={"type": "json_object"},  # D2219: A/B tested — valid JSON, no fence, 7% faster
    )

    result = parse_json_robust(raw)

    if isinstance(result, (dict, list)):
        return result

    # Last resort: try to extract JSON from the text
    repaired = repair_json(raw)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"OMLX response could not be parsed as JSON. "
            f"Raw (first 200 chars): {raw[:200]}... "
            f"Error: {e}"
        ) from e


def get_omlx_version() -> str | None:
    """Get OMLX server version.

    Tries health endpoint first, then falls back to binary --version.

    Returns:
        Version string (e.g. '0.4.4rc1') or None if unreachable.
    """
    # Try health endpoint
    try:
        headers = {"Authorization": f"Bearer {OMLX_API_KEY}"}
        resp = requests.get(f"{OMLX_URL}/health", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            ver = data.get("version")
            if ver:
                return ver
    except Exception:
        pass

    # Fallback: call omlx binary directly (path from pipeline_paths)
    import subprocess
    try:
        from pipeline.pipeline_paths import OMLX_BIN
        result = subprocess.run(
            [OMLX_BIN, "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    return None


def check_omlx_health() -> bool:
    """Check if OMLX is running and responsive (server-level).

    NOTE: This checks the /v1/models endpoint only. A True result
    does NOT guarantee chat completions work. Use stress_test_omlx()
    for a full pipeline-ready health check.

    Returns:
        True if OMLX server responds to API calls.
    """
    try:
        headers = {"Authorization": f"Bearer {OMLX_API_KEY}"}
        resp = requests.get(f"{OMLX_URL}/v1/models", headers=headers, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def stress_test_omlx(model: str = None, prompt_sizes: list[int] = None,
                     timeout: int = 30, verbose: bool = True) -> dict:
    """Stress-test OMLX chat completions at increasing prompt sizes.

    Unlike check_omlx_health() which only pings the API, this sends actual
    chat requests to verify the model is loaded, responding, and can handle
    real pipeline workloads. Detects the 'health endpoint lies' bug where
    /health returns ok but chat completions silently timeout.

    Args:
        model: Model to test (default: GEN_MODEL).
        prompt_sizes: List of prompt sizes in characters to test.
                      Default: [50, 1000, 5000] — tiny, small batch, real batch.
        timeout: Per-request timeout in seconds.
        verbose: Print progress to stdout.

    Returns:
        dict with: {'healthy': bool, 'results': [{size, elapsed, tokens, error}], 'verdict': str}
    """
    if model is None:
        model = GEN_MODEL
    if prompt_sizes is None:
        prompt_sizes = [50, 1000, 5000]

    results = []
    all_ok = True

    for size in prompt_sizes:
        # Build a prompt of approximately `size` characters
        base = "The quick brown fox jumps over the lazy dog. "
        repeats = max(1, size // len(base))
        prompt = (base * repeats)[:size]

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Respond with exactly: OK"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 20,
            "temperature": 0.0,
        }

        start = time.time()
        error = None
        tokens = 0
        try:
            headers = {"Authorization": f"Bearer {OMLX_API_KEY}"}
            resp = requests.post(
                f"{OMLX_URL}/v1/chat/completions",
                json=body,
                headers=headers,
                timeout=timeout,
            )
            elapsed = time.time() - start
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                tokens = len(content.split())
            else:
                error = f"HTTP {resp.status_code}: {resp.text[:150]}"
                elapsed = time.time() - start
                all_ok = False  # D2211: non-200 response = not healthy
        except requests.Timeout:
            elapsed = time.time() - start
            error = f"TIMEOUT after {elapsed:.0f}s"
            all_ok = False
        except Exception as e:
            elapsed = time.time() - start
            error = str(e)[:200]
            all_ok = False

        results.append({
            "size_chars": size,
            "elapsed_s": round(elapsed, 2),
            "tokens": tokens,
            "error": error,
            "passed": error is None,
        })

        if verbose:
            icon = "✅" if error is None else "❌"
            size_label = f"{size//1000}K" if size >= 1000 else f"{size}"
            detail = f"{elapsed:.1f}s, {tokens} tokens" if error is None else error
            print(f"  {icon} {size_label} chars → {detail}")

    verdict = "ALL_PASS" if all_ok else "FAIL"
    if all_ok:
        max_elapsed = max(r["elapsed_s"] for r in results)
        if max_elapsed > 10:
            verdict = "SLOW"
            if verbose:
                print(f"  ⚠️  Largest prompt took {max_elapsed:.1f}s — pipeline may be slow")

    return {
        "healthy": all_ok,
        "results": results,
        "verdict": verdict,
        "model": model,
    }


def generate(
    prompt: str,
    model: str = GEN_MODEL,
) -> str:
    """Shorthand alias for call_omlx (backward compat with old tool names)."""
    return call_omlx(prompt=prompt, model=model)


def verify(
    prompt: str,
    model: str = VERIFY_MODEL,
) -> str:
    """Call the verifier model (R5: different family than generator)."""
    return call_omlx(prompt=prompt, model=model)
