"""Peer failover client: G2A -> Sub2API OpenAI-compatible gateway.

When the local Grok account pool is exhausted / rate-limited / upstream-failing,
optionally forward the same Chat Completions request to a peer Sub2API instance.

Safety:
- Header X-Peer-Failover (or X-G2A-Peer-Failover) = 1 disables further peer hops
  to avoid G2A <-> Sub2 infinite recursion.
- Only non-streaming and streaming text chat are supported (no image/video).
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import time
from typing import Any, AsyncGenerator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.platform.config.snapshot import get_config
from app.platform.errors import RateLimitError, UpstreamError
from app.platform.logging.logger import logger

PEER_HEADER = "X-Peer-Failover"
PEER_HEADER_ALT = "X-G2A-Peer-Failover"

# Set by router when inbound request already came from a peer hop.
_peer_hop_blocked: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "g2a_peer_hop_blocked", default=False
)


def mark_inbound_peer_hop(blocked: bool = True) -> None:
    _peer_hop_blocked.set(bool(blocked))


def is_inbound_peer_hop() -> bool:
    return bool(_peer_hop_blocked.get())


def peer_enabled() -> bool:
    cfg = get_config()
    if not cfg.get_bool("peer.sub2_enabled", False):
        return False
    if is_inbound_peer_hop():
        return False
    base = (cfg.get_str("peer.sub2_base_url", "") or "").strip().rstrip("/")
    key = (cfg.get_str("peer.sub2_api_key", "") or "").strip()
    return bool(base and key)


def peer_prefer_local_first() -> bool:
    return get_config().get_bool("peer.prefer_local_first", True)


def peer_timeout_s() -> float:
    return float(get_config().get_float("peer.timeout_seconds", 90.0) or 90.0)


def peer_models_allow(model: str) -> bool:
    """Empty allowlist = all models; otherwise exact or prefix match."""
    cfg = get_config()
    allow = cfg.get_list("peer.models", default=[])
    if not allow:
        return True
    m = (model or "").strip().lower()
    for item in allow:
        s = str(item).strip().lower()
        if not s:
            continue
        if m == s or m.startswith(s):
            return True
    return False


def should_peer_on_exc(exc: BaseException) -> bool:
    """Whether local failure should trigger peer Sub2."""
    if not peer_enabled():
        return False
    cfg = get_config()
    codes = cfg.get_list("peer.on_status_codes", default=[429, 503, 502, 401, 403])
    code_set: set[int] = set()
    for c in codes:
        try:
            code_set.add(int(c))
        except (TypeError, ValueError):
            continue
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, UpstreamError):
        st = int(getattr(exc, "status", 0) or 0)
        if st in code_set or st == 0:
            return True
        # network-ish upstream
        if st >= 500:
            return True
    # selection exhausted messages sometimes raise RateLimitError already
    msg = str(exc).lower()
    if "no available" in msg or "rate limit" in msg:
        return True
    return False


def _peer_url(path: str = "/v1/chat/completions") -> str:
    cfg = get_config()
    base = (cfg.get_str("peer.sub2_base_url", "") or "").strip().rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def _peer_headers() -> dict[str, str]:
    cfg = get_config()
    key = (cfg.get_str("peer.sub2_api_key", "") or "").strip()
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        PEER_HEADER: "1",
        PEER_HEADER_ALT: "1",
    }


def _build_payload(
    *,
    model: str,
    messages: list[dict],
    stream: bool,
    temperature: float,
    top_p: float,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": bool(stream),
        "temperature": temperature,
        "top_p": top_p,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    return payload


def _sync_post_json(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
    req = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:  # nosec - local peer admin-configured
            return int(getattr(resp, "status", 200) or 200), resp.read()
    except HTTPError as e:
        data = e.read() if hasattr(e, "read") else b""
        return int(e.code or 502), data or str(e).encode("utf-8", errors="replace")
    except URLError as e:
        raise UpstreamError(f"Sub2 peer connection failed: {e}", status=502) from e
    except TimeoutError as e:
        raise UpstreamError("Sub2 peer timeout", status=504) from e


async def forward_to_sub2(
    *,
    model: str,
    messages: list[dict],
    stream: bool = False,
    temperature: float = 0.7,
    top_p: float = 0.95,
    max_tokens: int | None = 1024,
) -> dict | AsyncGenerator[str, None]:
    """Forward chat completion to peer Sub2API.

    Returns OpenAI-style dict for non-stream, or async generator of SSE lines for stream.
    """
    if not peer_enabled():
        raise UpstreamError("Sub2 peer not enabled", status=503)
    if not peer_models_allow(model):
        raise UpstreamError(f"Model {model} not allowed for Sub2 peer", status=400)

    url = _peer_url("/v1/chat/completions")
    headers = _peer_headers()
    timeout = peer_timeout_s()
    payload = _build_payload(
        model=model,
        messages=messages,
        stream=stream,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    logger.warning(
        "peer.sub2.forward start: model={} stream={} url={}",
        model,
        stream,
        url,
    )
    t0 = time.time()

    if stream:
        # Stream via iterative read in a worker thread using urllib (stdlib, no new deps).
        # For simplicity and reliability we call non-stream peer then re-emit as one SSE batch
        # if peer stream is hard; prefer true stream when possible with chunked reader.
        return _stream_from_peer(url, headers, body, timeout, model)

    status, raw = await asyncio.to_thread(_sync_post_json, url, headers, body, timeout)
    elapsed = int((time.time() - t0) * 1000)
    text = raw.decode("utf-8", errors="replace")
    if status >= 400:
        logger.warning(
            "peer.sub2.forward failed: status={} ms={} body={}",
            status,
            elapsed,
            text[:240],
        )
        raise UpstreamError(
            f"Sub2 peer returned {status}: {text[:200]}",
            status=status if status in (401, 403, 429, 502, 503, 504) else 502,
            body=text[:500],
        )
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise UpstreamError(f"Sub2 peer invalid JSON: {text[:200]}", status=502) from e
    logger.info("peer.sub2.forward ok: model={} ms={} status={}", model, elapsed, status)
    # annotate peer for observability without breaking clients
    if isinstance(data, dict):
        data.setdefault("system_fingerprint", "g2a-peer-sub2")
    return data


async def _stream_from_peer(
    url: str,
    headers: dict[str, str],
    body: bytes,
    timeout: float,
    model: str,
) -> AsyncGenerator[str, None]:
    """Best-effort SSE proxy: if peer stream fails, fall back to non-stream peer."""

    async def _gen() -> AsyncGenerator[str, None]:
        # Prefer non-stream peer then wrap as single completion SSE for clients that stream.
        # Avoids half-open stream complexity and matches G2A stream adapter expectations.
        try:
            non_stream_body = body
            # force stream=false in payload
            try:
                obj = json.loads(body.decode("utf-8"))
                obj["stream"] = False
                non_stream_body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            except Exception:
                pass
            status, raw = await asyncio.to_thread(
                _sync_post_json, url, headers, non_stream_body, timeout
            )
            text = raw.decode("utf-8", errors="replace")
            if status >= 400:
                raise UpstreamError(
                    f"Sub2 peer returned {status}: {text[:200]}",
                    status=status,
                    body=text[:500],
                )
            data = json.loads(text)
            content = ""
            try:
                content = (
                    ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
                    or ""
                )
            except Exception:
                content = ""
            rid = data.get("id") or f"chatcmpl-peer-{int(time.time()*1000)}"
            # emit as OpenAI SSE
            chunk = {
                "id": rid,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": data.get("model") or model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": content},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            end = {
                "id": rid,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": data.get("model") or model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(end, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            logger.info("peer.sub2.stream-wrap ok: model={}", model)
        except Exception as exc:
            logger.warning("peer.sub2.stream-wrap failed: error={}", exc)
            err = {
                "error": {
                    "message": f"Sub2 peer stream failed: {exc}",
                    "type": "upstream_error",
                }
            }
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return _gen()


async def try_peer_after_local_failure(
    *,
    model: str,
    messages: list[dict],
    stream: bool,
    temperature: float,
    top_p: float,
    exc: BaseException,
) -> dict | AsyncGenerator[str, None] | None:
    """Return peer result if eligible, else None (caller re-raises original)."""
    if not peer_models_allow(model):
        return None
    if not should_peer_on_exc(exc):
        return None
    try:
        return await forward_to_sub2(
            model=model,
            messages=messages,
            stream=stream,
            temperature=temperature,
            top_p=top_p,
        )
    except Exception as peer_exc:
        logger.warning(
            "peer.sub2.fallback failed after local error: local={} peer={}",
            type(exc).__name__,
            peer_exc,
        )
        return None


__all__ = [
    "PEER_HEADER",
    "PEER_HEADER_ALT",
    "mark_inbound_peer_hop",
    "is_inbound_peer_hop",
    "peer_enabled",
    "peer_prefer_local_first",
    "forward_to_sub2",
    "try_peer_after_local_failure",
    "should_peer_on_exc",
]
