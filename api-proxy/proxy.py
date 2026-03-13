#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 代理转发服务
────────────────────────────────────────────────────────────────
功能:
  1. 启动时自动调用 Token 接口获取 Token
  2. 后台每 30 分钟自动刷新 Token
  3. 透明转发所有请求到目标 API，自动在 Header 注入 Auth Token
  4. 支持 ChatGPT 流式响应 (SSE / stream: true)

依赖安装:
  pip install fastapi uvicorn[standard] httpx

启动:
  python proxy.py
  或: uvicorn proxy:app --host 0.0.0.0 --port 8080
────────────────────────────────────────────────────────────────
"""

import asyncio
import json
import logging
import os
import time
from typing import AsyncIterator, Optional

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

# ╔══════════════════════════════════════════════════════════════╗
# ║                    【配置区 - 必须修改】                      ║
# ╚══════════════════════════════════════════════════════════════╝

# ── Token 接口 ────────────────────────────────────────────────
# Token 接口地址（POST 请求）
TOKEN_API_URL = os.getenv(
    "TOKEN_API_URL",
    "https://your-auth-api.example.com/api/auth/token"   # ← 改为实际 Token 接口地址
)

# Token 接口请求体格式: "json" 或 "form"（application/x-www-form-urlencoded）
TOKEN_REQUEST_TYPE = os.getenv("TOKEN_REQUEST_TYPE", "json")

# 第一个参数
TOKEN_PARAM_1_NAME  = os.getenv("TOKEN_PARAM_1_NAME",  "username")       # ← 改为实际参数名
TOKEN_PARAM_1_VALUE = os.getenv("TOKEN_PARAM_1_VALUE", "your_username")  # ← 改为实际参数值

# 第二个参数
TOKEN_PARAM_2_NAME  = os.getenv("TOKEN_PARAM_2_NAME",  "password")       # ← 改为实际参数名
TOKEN_PARAM_2_VALUE = os.getenv("TOKEN_PARAM_2_VALUE", "your_password")  # ← 改为实际参数值

# ── 目标 API ─────────────────────────────────────────────────
# 目标接口完整地址（直接转发到此 URL，不拼接任何路径）
TARGET_API_URL = os.getenv(
    "TARGET_API_URL",
    "https://your-target-api.example.com/api/chat/send"  # ← 改为实际第二个接口的完整地址
)

# 目标接口鉴权 Header 字段名（默认 Auth，按实际接口要求修改）
AUTH_HEADER_NAME = os.getenv("AUTH_HEADER_NAME", "Auth")  # ← 改为实际 Header 字段名，如 Authorization、X-Token 等

# ── 代理服务监听配置 ──────────────────────────────────────────
PROXY_HOST = os.getenv("PROXY_HOST", "0.0.0.0")         # 0.0.0.0 允许外部访问
PROXY_PORT = int(os.getenv("PROXY_PORT", "8080"))        # ← 改为期望监听的端口

# 对外暴露的固定路径（仅这两个路径接收请求并转发）
LOCAL_PATHS = ["/v1/chat/completions", "/v1/responses"]

# ── Token 刷新间隔 ────────────────────────────────────────────
TOKEN_REFRESH_INTERVAL = int(os.getenv("TOKEN_REFRESH_INTERVAL", str(30 * 60)))  # 默认 30 分钟

# ╔══════════════════════════════════════════════════════════════╗
# ║                  【以下代码无需修改】                         ║
# ╚══════════════════════════════════════════════════════════════╝

# ── 日志配置 ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("proxy.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# hop-by-hop headers 不应透传
_HOP_BY_HOP = frozenset({
    "host", "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade",
})

# 流式响应头不应透传（会导致 nginx 缓冲）
_EXCLUDE_RESP_HEADERS = frozenset({
    "content-encoding", "transfer-encoding", "connection", "keep-alive",
})


# ── Token 管理器 ──────────────────────────────────────────────
class TokenManager:
    """
    线程安全的 Token 管理器。
    - get_token(): 按需获取，过期则自动刷新
    - force_refresh(): 强制刷新（后台定时任务使用）
    """

    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._last_refresh: float = 0.0
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        async with self._lock:
            if self._need_refresh():
                await self._do_refresh()
        return self._token  # type: ignore[return-value]

    async def force_refresh(self) -> None:
        async with self._lock:
            await self._do_refresh()

    def _need_refresh(self) -> bool:
        return (
            self._token is None
            or (time.monotonic() - self._last_refresh) >= TOKEN_REFRESH_INTERVAL
        )

    async def _do_refresh(self) -> None:
        """实际发起 Token 请求（调用方持有锁）"""
        payload = {
            TOKEN_PARAM_1_NAME: TOKEN_PARAM_1_VALUE,
            TOKEN_PARAM_2_NAME: TOKEN_PARAM_2_VALUE,
        }
        logger.info("正在刷新 Token，接口: %s", TOKEN_API_URL)
        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False, trust_env=False) as client:
                if TOKEN_REQUEST_TYPE == "form":
                    resp = await client.post(TOKEN_API_URL, data=payload)
                else:
                    resp = await client.post(TOKEN_API_URL, json=payload)

            resp.raise_for_status()
            data: dict = resp.json()

            # 校验业务状态
            status_code = data.get("status", {}).get("statusCode", "")
            if status_code != "SUCCESS":
                raise ValueError(
                    f"Token 接口业务状态非 SUCCESS，实际: {status_code!r}，响应: {data}"
                )

            token = data.get("result")
            if not token:
                raise ValueError(f"result 字段为空，完整响应: {data}")

            self._token = str(token)
            self._last_refresh = time.monotonic()
            logger.info("Token 刷新成功（长度 %d）", len(self._token))

        except Exception as exc:
            logger.error("Token 刷新失败: %s", exc)
            if self._token is None:
                # 启动阶段失败则直接退出
                raise RuntimeError(f"初始 Token 获取失败，服务无法启动: {exc}") from exc
            logger.warning("刷新失败，继续使用旧 Token")


# ── 全局 Token 管理器实例 ─────────────────────────────────────
token_manager = TokenManager()


# ── FastAPI 应用 ─────────────────────────────────────────────
app = FastAPI(title="API Proxy", version="1.0.0")


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("=" * 60)
    logger.info("API 代理服务启动")
    logger.info("目标接口: %s", TARGET_API_URL)
    logger.info("对外路径: %s", ", ".join(LOCAL_PATHS))
    logger.info("Token 刷新间隔: %d 秒", TOKEN_REFRESH_INTERVAL)
    logger.info("监听地址: %s:%d", PROXY_HOST, PROXY_PORT)
    logger.info("=" * 60)

    # 启动时同步获取 Token（失败则退出）
    await token_manager.get_token()

    # 启动后台定时刷新任务
    asyncio.create_task(_background_refresh_loop(), name="token-refresh")
    logger.info("后台 Token 刷新任务已启动")


async def _background_refresh_loop() -> None:
    """每隔 TOKEN_REFRESH_INTERVAL 秒强制刷新一次 Token"""
    while True:
        await asyncio.sleep(TOKEN_REFRESH_INTERVAL)
        try:
            await token_manager.force_refresh()
        except Exception as exc:
            logger.error("后台 Token 刷新异常: %s", exc)


# ── 工具函数 ─────────────────────────────────────────────────
def _detect_stream(body: bytes) -> bool:
    """从请求体中检测是否为流式请求（ChatGPT 格式: {"stream": true}）"""
    if not body or b"stream" not in body:
        return False
    try:
        return bool(json.loads(body).get("stream", False))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False


def _build_forward_headers(request: Request, token: str) -> dict:
    """构造转发请求头：过滤 hop-by-hop，强制用内部 Token 覆盖同名鉴权字段"""
    auth_key_lower = AUTH_HEADER_NAME.lower()
    headers = {
        k: v
        for k, v in request.headers.items()
        # 过滤 hop-by-hop，同时剔除外部传入的同名鉴权字段（无论大小写），防止外部 token 透传
        if k.lower() not in _HOP_BY_HOP and k.lower() != auth_key_lower
    }
    headers[AUTH_HEADER_NAME] = token  # 注入内部管理的 Token，始终覆盖外部传值
    return headers


def _build_resp_headers(resp: httpx.Response) -> dict:
    """构造响应头：过滤掉不应透传的头"""
    return {
        k: v
        for k, v in resp.headers.items()
        if k.lower() not in _EXCLUDE_RESP_HEADERS
    }


# ── Responses API ↔ Chat Completions 格式转换 ─────────────────

def _responses_to_chat_body(data: dict) -> dict:
    """
    OpenAI Responses API 请求体 → Chat Completions 请求体
    主要差异:
      input / instructions → messages
      max_output_tokens    → max_tokens
    """
    out: dict = {}

    # 通用字段直接透传
    for k in ("model", "stream", "temperature", "top_p", "n",
              "stop", "presence_penalty", "frequency_penalty", "user"):
        if k in data:
            out[k] = data[k]

    # max_output_tokens → max_tokens
    if "max_output_tokens" in data:
        out["max_tokens"] = data["max_output_tokens"]
    elif "max_tokens" in data:
        out["max_tokens"] = data["max_tokens"]

    # 构造 messages
    messages: list = []

    # instructions → system message
    if data.get("instructions"):
        messages.append({"role": "system", "content": data["instructions"]})

    # input → messages（支持字符串、消息列表两种形式）
    inp = data.get("input", [])
    if isinstance(inp, str):
        messages.append({"role": "user", "content": inp})
    elif isinstance(inp, list):
        for item in inp:
            if isinstance(item, dict):
                messages.append({
                    "role": item.get("role", "user"),
                    "content": item.get("content", ""),
                })

    out["messages"] = messages
    return out


def _chat_to_responses_body(data: dict) -> dict:
    """
    Chat Completions 响应体 → Responses API 响应体（非流式）
    """
    choice = (data.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    usage = data.get("usage") or {}

    rid = data.get("id") or ""
    resp_id = f"resp_{rid}" if rid and not rid.startswith("resp_") else (rid or f"resp_{int(time.time())}")

    return {
        "id": resp_id,
        "object": "response",
        "created_at": data.get("created", int(time.time())),
        "status": "completed",
        "model": data.get("model", ""),
        "output": [{
            "id": "msg_001",
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": text, "annotations": []}],
        }],
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
        "error": None,
        "incomplete_details": None,
        "instructions": None,
        "metadata": {},
        "parallel_tool_calls": True,
        "temperature": data.get("temperature", 1.0),
        "tool_choice": "auto",
        "tools": [],
        "top_p": data.get("top_p", 1.0),
        "truncation": "disabled",
    }


def _sse(event_type: str, data: dict) -> bytes:
    """生成一条 SSE 事件"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


async def _responses_stream_adapter(
    source: AsyncIterator[bytes],
) -> AsyncIterator[bytes]:
    """
    将 Chat Completions SSE 流逐块转换为 Responses API SSE 事件流。
    Chat 格式: data: {"choices":[{"delta":{"content":"..."}}]}
    Responses 格式: event: response.output_text.delta / response.done 等
    """
    resp_id = f"resp_{int(time.time())}"
    item_id = "msg_001"
    model = ""
    full_text = ""
    usage: dict = {}
    started = False
    buf = b""

    async for raw in source:
        buf += raw
        # SSE 事件之间以 \n\n 分隔
        while b"\n\n" in buf:
            block, buf = buf.split(b"\n\n", 1)
            for line in block.splitlines():
                line = line.strip()
                if not line.startswith(b"data:"):
                    continue
                payload = line[5:].strip().decode("utf-8", errors="replace")

                if payload == "[DONE]":
                    yield _sse("response.output_text.done", {
                        "type": "response.output_text.done",
                        "item_id": item_id, "output_index": 0, "content_index": 0,
                        "text": full_text,
                    })
                    yield _sse("response.output_item.done", {
                        "type": "response.output_item.done", "output_index": 0,
                        "item": {
                            "id": item_id, "type": "message", "role": "assistant",
                            "status": "completed",
                            "content": [{"type": "output_text", "text": full_text, "annotations": []}],
                        },
                    })
                    yield _sse("response.done", {
                        "type": "response.done",
                        "response": {
                            "id": resp_id, "object": "response", "status": "completed",
                            "model": model, "created_at": int(time.time()),
                            "output": [{
                                "id": item_id, "type": "message", "role": "assistant",
                                "status": "completed",
                                "content": [{"type": "output_text", "text": full_text, "annotations": []}],
                            }],
                            "usage": {
                                "input_tokens": usage.get("prompt_tokens", 0),
                                "output_tokens": usage.get("completion_tokens", 0),
                                "total_tokens": usage.get("total_tokens", 0),
                            },
                        },
                    })
                    yield b"data: [DONE]\n\n"
                    return

                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                # 第一个有效 chunk：发送 created / output_item.added / content_part.added
                if not started:
                    model = chunk.get("model", "")
                    cid = chunk.get("id", "")
                    resp_id = f"resp_{cid}" if cid else resp_id
                    yield _sse("response.created", {
                        "type": "response.created",
                        "response": {
                            "id": resp_id, "object": "response",
                            "status": "in_progress", "model": model,
                            "output": [], "usage": None,
                        },
                    })
                    yield _sse("response.output_item.added", {
                        "type": "response.output_item.added", "output_index": 0,
                        "item": {"id": item_id, "type": "message",
                                 "role": "assistant", "content": [], "status": "in_progress"},
                    })
                    yield _sse("response.content_part.added", {
                        "type": "response.content_part.added",
                        "item_id": item_id, "output_index": 0, "content_index": 0,
                        "part": {"type": "output_text", "text": "", "annotations": []},
                    })
                    started = True

                # 增量文本
                choices = chunk.get("choices") or []
                if choices:
                    delta_content = (choices[0].get("delta") or {}).get("content") or ""
                    if delta_content:
                        full_text += delta_content
                        yield _sse("response.output_text.delta", {
                            "type": "response.output_text.delta",
                            "item_id": item_id, "output_index": 0, "content_index": 0,
                            "delta": delta_content,
                        })

                # 记录 usage（部分上游会在最后一个 chunk 里带）
                if chunk.get("usage"):
                    usage = chunk["usage"]


def _log_messages(body: bytes, local_path: str) -> None:
    """打印实际发出请求的 model 和 messages 内容（已经过格式转换后的 chat 格式）"""
    if not body:
        return
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return
    model = data.get("model", "-")
    # 兼容 chat 格式 (messages) 和 responses 格式 (input)
    messages = data.get("messages") or []
    inp = data.get("input")
    if not messages and inp:
        if isinstance(inp, str):
            messages = [{"role": "user", "content": inp}]
        elif isinstance(inp, list):
            messages = inp
    logger.info("  path=%s  model=%s  messages=%d 条", local_path, model, len(messages))
    for i, msg in enumerate(messages):
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if isinstance(content, list):
            text = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        else:
            text = str(content)
        preview = text[:200].replace("\n", "\\n")
        if len(text) > 200:
            preview += f"…(+{len(text) - 200})"
        logger.info("  [%d] %s: %s", i, role, preview)


# ── 代理路由（仅 /v1/chat/completions 和 /v1/responses）────────
async def _proxy_handler(request: Request, local_path: str) -> Response:
    is_responses = (local_path == "/v1/responses")

    # 1. 获取有效 Token
    token = await token_manager.get_token()

    # 2. 目标 URL 直接使用完整配置地址，不拼接路径
    target_url = TARGET_API_URL
    query_string = request.url.query
    if query_string:
        target_url += f"?{query_string}"

    # 3. 构造请求头
    forward_headers = _build_forward_headers(request, token)

    # 4. 读取请求体
    body = await request.body()

    # 5. /v1/responses → 转换为 chat completions 格式再转发
    original_body = body
    if is_responses and body:
        try:
            req_data = json.loads(body)
            logger.info("  [RAW REQUEST BODY]\n%s",
                        json.dumps(req_data, ensure_ascii=False, indent=2))
            chat_data = _responses_to_chat_body(req_data)
            body = json.dumps(chat_data, ensure_ascii=False).encode("utf-8")
            forward_headers["content-type"] = "application/json"
            forward_headers["content-length"] = str(len(body))
            logger.info("  [CONVERTED REQUEST BODY]\n%s",
                        json.dumps(chat_data, ensure_ascii=False, indent=2))
        except Exception as exc:
            logger.warning("  [responses→chat] 转换失败，原样转发: %s", exc)
            logger.warning("  [RAW REQUEST BODY raw bytes] %s", original_body[:500])

    # 6. 判断是否流式（转换后的 body）
    is_stream = _detect_stream(body)

    logger.info(
        "→ %s %s → %s | stream=%s | body=%d bytes",
        request.method, local_path, target_url, is_stream, len(body),
    )
    logger.info("  [FORWARD HEADERS] %s",
                {k: v for k, v in forward_headers.items() if k.lower() != AUTH_HEADER_NAME.lower()})
    _log_messages(body, local_path)

    # 7. 转发
    if is_stream:
        if is_responses:
            return _stream_responses_response(request.method, target_url, forward_headers, body)
        return await _proxy_stream(request.method, target_url, forward_headers, body)
    else:
        resp = await _proxy_normal(request.method, target_url, forward_headers, body)
        # 无论状态码，都打印响应体便于排查
        try:
            resp_text = resp.body.decode("utf-8", errors="replace")
            logger.info("  [RESPONSE %d] %s", resp.status_code, resp_text[:2000])
        except Exception:
            pass
        if is_responses and resp.status_code == 200:
            try:
                chat_resp = json.loads(resp.body)
                responses_resp = _chat_to_responses_body(chat_resp)
                logger.info("  [chat→responses] 响应体已转换")
                return Response(
                    content=json.dumps(responses_resp, ensure_ascii=False).encode("utf-8"),
                    status_code=200,
                    media_type="application/json",
                )
            except Exception as exc:
                logger.warning("  [chat→responses] 转换失败，原样返回: %s", exc)
        return resp


def _stream_responses_response(
    method: str, url: str, headers: dict, body: bytes
) -> StreamingResponse:
    """流式 /v1/responses：从 chat SSE 流转换为 Responses API SSE 事件流"""

    async def _gen():
        async def _chat_chunks() -> AsyncIterator[bytes]:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0),
                follow_redirects=True, verify=False, trust_env=False,
            ) as client:
                async with client.stream(method=method, url=url, headers=headers, content=body) as resp:
                    logger.info("← %d (stream/responses) %s", resp.status_code, url)
                    async for chunk in resp.aiter_bytes(chunk_size=512):
                        if chunk:
                            yield chunk

        async for event_bytes in _responses_stream_adapter(_chat_chunks()):
            yield event_bytes

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.api_route("/v1/chat/completions", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def chat_completions(request: Request) -> Response:
    return await _proxy_handler(request, "/v1/chat/completions")


@app.api_route("/v1/responses", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def responses(request: Request) -> Response:
    return await _proxy_handler(request, "/v1/responses")


async def _proxy_normal(
    method: str, url: str, headers: dict, body: bytes
) -> Response:
    """转发普通请求，返回完整响应"""
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True, verify=False, trust_env=False) as client:
        resp = await client.request(
            method=method, url=url, headers=headers, content=body
        )

    logger.info("← %d %s", resp.status_code, url)
    if resp.status_code >= 400:
        logger.error("  [ERROR RESPONSE %d] headers=%s body=%s",
                     resp.status_code, dict(resp.headers),
                     resp.text[:2000])
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=_build_resp_headers(resp),
        media_type=resp.headers.get("content-type"),
    )


async def _proxy_stream(
    method: str, url: str, headers: dict, body: bytes
) -> StreamingResponse:
    """转发流式请求，逐块返回 SSE 数据"""

    async def _chunk_generator():
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0),
            follow_redirects=True,
            verify=False,
            trust_env=False,
        ) as client:
            async with client.stream(
                method=method, url=url, headers=headers, content=body
            ) as resp:
                logger.info("← %d (stream) %s", resp.status_code, url)
                async for chunk in resp.aiter_bytes(chunk_size=512):
                    if chunk:
                        yield chunk

    return StreamingResponse(
        _chunk_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # 告知 Nginx 不要缓冲
            "Connection": "keep-alive",
        },
    )


# ── 健康检查 ─────────────────────────────────────────────────
@app.get("/_proxy/health")
async def health() -> dict:
    """代理服务健康检查（不转发到目标 API）"""
    has_token = token_manager._token is not None
    age = int(time.monotonic() - token_manager._last_refresh) if has_token else -1
    return {
        "status": "ok",
        "has_token": has_token,
        "token_age_seconds": age,
        "refresh_interval_seconds": TOKEN_REFRESH_INTERVAL,
        "target": TARGET_API_URL,
        "local_paths": LOCAL_PATHS,
    }


# ── 入口 ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=PROXY_HOST,
        port=PROXY_PORT,
        log_level="info",
        access_log=False,   # 访问日志由 logger 接管，避免重复
    )
