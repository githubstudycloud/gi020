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
from typing import Optional

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

# 对外暴露的路径前缀（该前缀下所有路径均转发到 TARGET_API_URL）
# 默认 /v1，支持 /v1/chat/completions、/v1/responses 等所有 /v1/* 路径
LOCAL_API_PREFIX = os.getenv("LOCAL_API_PREFIX", "/v1")  # ← 可按需修改

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
    logger.info("本地前缀: %s/*  (支持 /chat/completions、/responses 等)", LOCAL_API_PREFIX)
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


# ── 代理路由（LOCAL_API_PREFIX/* 均转发到完整目标 URL）────────
# 例: /v1/chat/completions、/v1/responses、/v1/embeddings ... 全部命中
@app.api_route(
    LOCAL_API_PREFIX.rstrip("/") + "/{rest_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
)
async def proxy_handler(request: Request, rest_path: str) -> Response:
    local_path = f"{LOCAL_API_PREFIX.rstrip('/')}/{rest_path}"

    # 1. 获取有效 Token
    token = await token_manager.get_token()

    # 2. 目标 URL 直接使用完整配置地址，不拼接路径
    target_url = TARGET_API_URL
    query_string = request.url.query
    if query_string:
        target_url += f"?{query_string}"

    # 3. 构造请求头（外部同名鉴权字段已被剔除，内部 Token 强制注入）
    forward_headers = _build_forward_headers(request, token)

    # 4. 读取请求体
    body = await request.body()

    # 5. 判断是否流式
    is_stream = _detect_stream(body)

    logger.info(
        "→ %s %s → %s | stream=%s | body=%d bytes",
        request.method, local_path, target_url, is_stream, len(body),
    )

    # 6. 转发
    if is_stream:
        return await _proxy_stream(request.method, target_url, forward_headers, body)
    else:
        return await _proxy_normal(request.method, target_url, forward_headers, body)


async def _proxy_normal(
    method: str, url: str, headers: dict, body: bytes
) -> Response:
    """转发普通请求，返回完整响应"""
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True, verify=False, trust_env=False) as client:
        resp = await client.request(
            method=method, url=url, headers=headers, content=body
        )

    logger.info("← %d %s", resp.status_code, url)
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
        "local_prefix": LOCAL_API_PREFIX,
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
