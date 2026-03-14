#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 代理转发服务 v2.0
────────────────────────────────────────────────────────────────
功能:
  1. 启动时自动调用 Token 接口获取 Token
  2. 后台每 30 分钟自动刷新 Token
  3. 透明转发请求到目标 API，自动在 Header 注入 Auth Token
  4. 支持 /v1/responses ↔ Chat Completions 双向格式转换
  5. 完整适配 GLM 系列（glm-4/glm-4-flash/glm-z1/glm-4v 等）
     - reasoning_content / reasoning 字段（GLM-Z1）
     - extra.usage 流式用量字段
     - web_search / code_interpreter / retrieval 内置工具
     - completion_tokens_details.reasoning_tokens 用量映射
  6. OpenAI Responses API 2025 最新规格
     - tools 平铺格式 → function 嵌套格式
     - tool_choice 格式转换
     - text.format → response_format（json_schema/json_object）
     - function_call / function_call_output 输入项转换
     - 多模态图片内容（input_image → image_url）
     - finish_reason → stop_reason 精确映射
     - incomplete_details（length / content_filter）
  7. SKIP_TOKEN_AUTH 模式：直接透传 Authorization 头

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
TOKEN_PARAM_1_NAME  = os.getenv("TOKEN_PARAM_1_NAME",  "username")
TOKEN_PARAM_1_VALUE = os.getenv("TOKEN_PARAM_1_VALUE", "your_username")

# 第二个参数
TOKEN_PARAM_2_NAME  = os.getenv("TOKEN_PARAM_2_NAME",  "password")
TOKEN_PARAM_2_VALUE = os.getenv("TOKEN_PARAM_2_VALUE", "your_password")

# ── 目标 API ─────────────────────────────────────────────────
TARGET_API_URL = os.getenv(
    "TARGET_API_URL",
    "https://your-target-api.example.com/api/chat/send"  # ← 改为实际接口地址
)

# 鉴权 Header 字段名
AUTH_HEADER_NAME = os.getenv("AUTH_HEADER_NAME", "Auth")

# ── 跳过 Token 认证（直接使用客户端 Authorization，适合标准 OpenAI key 模式）──
# 设为 true 时：不调用 Token 接口，直接透传客户端 Authorization 头
SKIP_TOKEN_AUTH = os.getenv("SKIP_TOKEN_AUTH", "false").lower() in ("1", "true", "yes")

# ── 代理服务监听配置 ──────────────────────────────────────────
PROXY_HOST = os.getenv("PROXY_HOST", "0.0.0.0")
PROXY_PORT = int(os.getenv("PROXY_PORT", "8080"))

LOCAL_PATHS = ["/v1/chat/completions", "/v1/responses"]

# ── Token 刷新间隔 ────────────────────────────────────────────
TOKEN_REFRESH_INTERVAL = int(os.getenv("TOKEN_REFRESH_INTERVAL", str(30 * 60)))

# ╔══════════════════════════════════════════════════════════════╗
# ║                  【以下代码无需修改】                         ║
# ╚══════════════════════════════════════════════════════════════╝

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

_HOP_BY_HOP = frozenset({
    "host", "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade",
})

_EXCLUDE_RESP_HEADERS = frozenset({
    "content-encoding", "transfer-encoding", "connection", "keep-alive",
})

# ── finish_reason → Responses API stop_reason 映射 ─────────────
_FINISH_TO_STOP: dict = {
    "stop":           "end_turn",
    "eos":            "end_turn",          # 部分模型使用 eos
    "length":         "max_tokens",
    "max_tokens":     "max_tokens",
    "tool_calls":     "tool_calls",
    "function_call":  "tool_calls",        # 旧版 OpenAI 字段名
    "content_filter": "content_filter",
    "sensitive":      "content_filter",    # GLM 内容过滤
    "abort":          "end_turn",          # GLM 流中断
    "error":          "end_turn",          # GLM 错误中断
}

# ── Responses API 内置工具类型 → Chat Completions/GLM 工具格式 ──
# None 表示该工具类型不被 GLM 支持，直接过滤
_BUILTIN_TOOL_MAP: dict = {
    # OpenAI Responses API → GLM 原生内置工具
    "web_search_preview":       {"type": "web_search"},
    "web_search_preview_2025":  {"type": "web_search"},
    "code_interpreter":         {"type": "code_interpreter"},
    # GLM 用 retrieval，无法从 Responses API 直接映射，过滤
    "file_search":              None,
    # GLM 不支持
    "computer_use_preview":     None,
    "image_generation":         None,
}


# ── Token 管理器 ──────────────────────────────────────────────
class TokenManager:
    """
    线程安全的 Token 管理器。
    SKIP_TOKEN_AUTH=true 时所有方法为 no-op，token 恒为空字符串。
    """

    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._last_refresh: float = 0.0
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        if SKIP_TOKEN_AUTH:
            return ""
        async with self._lock:
            if self._need_refresh():
                await self._do_refresh()
        return self._token or ""

    async def force_refresh(self) -> None:
        if SKIP_TOKEN_AUTH:
            return
        async with self._lock:
            await self._do_refresh()

    def _need_refresh(self) -> bool:
        return (
            self._token is None
            or (time.monotonic() - self._last_refresh) >= TOKEN_REFRESH_INTERVAL
        )

    async def _do_refresh(self) -> None:
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
                raise RuntimeError(f"初始 Token 获取失败，服务无法启动: {exc}") from exc
            logger.warning("刷新失败，继续使用旧 Token")


token_manager = TokenManager()
app = FastAPI(title="API Proxy", version="2.0.0")


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("=" * 60)
    logger.info("API 代理服务启动 v2.0")
    logger.info("目标接口: %s", TARGET_API_URL)
    logger.info("跳过 Token 认证: %s", SKIP_TOKEN_AUTH)
    logger.info("Token 刷新间隔: %d 秒", TOKEN_REFRESH_INTERVAL)
    logger.info("监听地址: %s:%d", PROXY_HOST, PROXY_PORT)
    logger.info("=" * 60)

    await token_manager.get_token()
    asyncio.create_task(_background_refresh_loop(), name="token-refresh")
    logger.info("后台 Token 刷新任务已启动")


async def _background_refresh_loop() -> None:
    while True:
        await asyncio.sleep(TOKEN_REFRESH_INTERVAL)
        try:
            await token_manager.force_refresh()
        except Exception as exc:
            logger.error("后台 Token 刷新异常: %s", exc)


# ── 工具函数 ─────────────────────────────────────────────────
def _detect_stream(body: bytes) -> bool:
    if not body or b"stream" not in body:
        return False
    try:
        return bool(json.loads(body).get("stream", False))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False


def _build_forward_headers(request: Request, token: str) -> dict:
    """
    构造转发请求头。
    - SKIP_TOKEN_AUTH=false: 过滤外部鉴权头，注入内部 Token
    - SKIP_TOKEN_AUTH=true : 保留客户端 Authorization 头原样透传
    """
    auth_key_lower = AUTH_HEADER_NAME.lower()
    if SKIP_TOKEN_AUTH:
        # 直接透传，只过滤 hop-by-hop
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in _HOP_BY_HOP
        }
    else:
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in _HOP_BY_HOP and k.lower() != auth_key_lower
        }
        if token:
            headers[AUTH_HEADER_NAME] = token
    return headers


def _build_resp_headers(resp: httpx.Response) -> dict:
    return {
        k: v for k, v in resp.headers.items()
        if k.lower() not in _EXCLUDE_RESP_HEADERS
    }


# ── Responses API ↔ Chat Completions 格式转换 ─────────────────

def _extract_content_parts(content):
    """
    Responses API content → Chat Completions content。
    - 纯文本 → str
    - 含图片 → list（多模态，Chat Completions 格式）

    支持的 Responses API content part 类型:
      input_text / output_text / text → {"type": "text", "text": "..."}
      input_image (image_url)         → {"type": "image_url", "image_url": {...}}
      input_image (source.base64)     → {"type": "image_url", "image_url": {"url": "data:..."}}
      input_image (source.url)        → {"type": "image_url", "image_url": {"url": "..."}}
    """
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content) if content else ""

    TEXT_TYPES = {"input_text", "output_text", "text"}
    parts: list = []
    has_non_text = False

    for part in content:
        if not isinstance(part, dict):
            continue
        part_type = part.get("type", "")

        if part_type in TEXT_TYPES:
            parts.append({"type": "text", "text": part.get("text", "")})

        elif part_type == "input_image":
            has_non_text = True
            detail = part.get("detail", "auto")
            img_url = part.get("image_url")
            source = part.get("source")

            if img_url:
                if isinstance(img_url, str):
                    parts.append({"type": "image_url",
                                  "image_url": {"url": img_url, "detail": detail}})
                else:
                    # 已是 dict，补充 detail
                    img_obj = dict(img_url)
                    img_obj.setdefault("detail", detail)
                    parts.append({"type": "image_url", "image_url": img_obj})
            elif source:
                src_type = source.get("type", "")
                if src_type == "base64":
                    b64 = (f"data:{source.get('media_type','image/jpeg')}"
                           f";base64,{source.get('data','')}")
                    parts.append({"type": "image_url",
                                  "image_url": {"url": b64, "detail": detail}})
                elif src_type == "url":
                    parts.append({"type": "image_url",
                                  "image_url": {"url": source.get("url", ""),
                                                "detail": detail}})

        elif part_type == "image_url":
            # 客户端已传 Chat Completions 格式，直接保留
            has_non_text = True
            parts.append({"type": "image_url", "image_url": part.get("image_url", {})})

        # 其他未知 part 类型忽略

    if not parts:
        return ""
    if not has_non_text:
        # 纯文本，合并为字符串
        return "\n".join(p.get("text", "") for p in parts)
    return parts


# 保持旧名称兼容
def _extract_content(content) -> str:
    result = _extract_content_parts(content)
    return result if isinstance(result, str) else (
        "\n".join(
            p.get("text", "") for p in result
            if isinstance(p, dict) and p.get("type") == "text"
        ) if isinstance(result, list) else str(result)
    )


def _convert_tools_to_chat(tools: list) -> list:
    """
    Responses API tools → Chat Completions / GLM tools。

    转换规则:
    1. function 工具（平铺）  → function 工具（嵌套 function 键）
    2. function 工具（已嵌套）→ 直接透传
    3. 内置工具类型映射:
         web_search_preview / web_search_preview_2025 → {"type": "web_search"}（GLM）
         code_interpreter                             → {"type": "code_interpreter"}（GLM）
         file_search / computer_use_preview 等        → 过滤（GLM 不支持）
    4. 未知类型（含 GLM 原生 web_search/retrieval）   → 直接透传
    """
    converted = []
    for tool in tools:
        if not isinstance(tool, dict):
            converted.append(tool)
            continue
        tool_type = tool.get("type", "")

        if tool_type == "function":
            if "function" not in tool:
                # Responses API 平铺格式 → Chat Completions 嵌套格式
                fn_obj: dict = {"name": tool.get("name", "")}
                for k in ("description", "parameters", "strict"):
                    if k in tool:
                        fn_obj[k] = tool[k]
                converted.append({"type": "function", "function": fn_obj})
            else:
                # 已是嵌套格式，直接透传
                converted.append(tool)

        elif tool_type in _BUILTIN_TOOL_MAP:
            mapped = _BUILTIN_TOOL_MAP[tool_type]
            if mapped is not None:
                converted.append(mapped)
            # mapped=None 时过滤该工具

        else:
            # 未知类型（GLM 原生 web_search / retrieval / code_interpreter 等）直接透传
            converted.append(tool)

    return converted


def _convert_tool_choice(tool_choice):
    """
    Responses API tool_choice → Chat Completions tool_choice。

    Responses API: {"type": "function", "name": "func_name"}
    Chat Completions: {"type": "function", "function": {"name": "func_name"}}
    字符串 ("auto" / "none" / "required") 直接透传。
    """
    if isinstance(tool_choice, dict):
        tc_type = tool_choice.get("type", "")
        if tc_type == "function" and "function" not in tool_choice and "name" in tool_choice:
            return {"type": "function", "function": {"name": tool_choice["name"]}}
    return tool_choice


def _convert_response_format(data: dict) -> Optional[dict]:
    """
    Responses API text.format → Chat Completions response_format。

    text.format.type = "json_schema"
      → {"type": "json_schema", "json_schema": {"name":..., "schema":..., "strict":...}}
    text.format.type = "json_object"
      → {"type": "json_object"}
    text.format.type = "text" 或未设置
      → None（默认，不添加 response_format）
    """
    text = data.get("text") or {}
    fmt = text.get("format") or {}
    fmt_type = fmt.get("type", "")

    if fmt_type == "json_schema":
        json_schema: dict = {"name": fmt.get("name", "response")}
        if "schema" in fmt:
            json_schema["schema"] = fmt["schema"]
        if "strict" in fmt:
            json_schema["strict"] = fmt["strict"]
        if "description" in fmt:
            json_schema["description"] = fmt["description"]
        return {"type": "json_schema", "json_schema": json_schema}

    if fmt_type == "json_object":
        return {"type": "json_object"}

    return None


def _responses_to_chat_body(data: dict) -> dict:
    """
    OpenAI Responses API 请求体 → Chat Completions 请求体。

    ┌──────────────────────────────────────────────────────────────┐
    │ Responses API 字段            → Chat Completions 字段         │
    ├──────────────────────────────────────────────────────────────┤
    │ instructions                  → messages[0]{role:system}      │
    │ input (str)                   → messages[{role:user}]         │
    │ input[{role:user/assistant}]  → messages                      │
    │ input[{type:function_call}]   → messages[{role:assistant,     │
    │                                           tool_calls:[...]}]  │
    │ input[{type:function_call_output}] → messages[{role:tool}]   │
    │ max_output_tokens             → max_tokens                    │
    │ tools (平铺 function)          → tools (嵌套 function)         │
    │ tools (内置类型)               → GLM 内置工具 / 过滤            │
    │ tool_choice {type,name}       → tool_choice {function:{name}} │
    │ text.format (json_schema 等)  → response_format               │
    │ input_image content parts     → image_url content parts       │
    │ seed / logprobs / top_logprobs → 直接透传                     │
    └──────────────────────────────────────────────────────────────┘
    """
    out: dict = {}

    # 通用字段直接透传
    for k in ("model", "stream", "temperature", "top_p", "n",
              "stop", "presence_penalty", "frequency_penalty", "user",
              "parallel_tool_calls", "seed", "logprobs", "top_logprobs",
              "service_tier"):
        if k in data:
            out[k] = data[k]

    # max_output_tokens → max_tokens
    if "max_output_tokens" in data:
        out["max_tokens"] = data["max_output_tokens"]
    elif "max_tokens" in data:
        out["max_tokens"] = data["max_tokens"]

    # tools: 格式转换 + 内置工具映射
    if data.get("tools"):
        converted_tools = _convert_tools_to_chat(data["tools"])
        if converted_tools:
            out["tools"] = converted_tools

    # tool_choice: 格式转换
    if "tool_choice" in data:
        out["tool_choice"] = _convert_tool_choice(data["tool_choice"])

    # text.format → response_format
    rf = _convert_response_format(data)
    if rf:
        out["response_format"] = rf

    # GLM meta 字段（角色扮演）直接透传
    if "meta" in data:
        out["meta"] = data["meta"]

    # 构造 messages
    messages: list = []

    # instructions → system message（放在最前）
    if data.get("instructions"):
        messages.append({"role": "system", "content": data["instructions"]})

    # input → messages
    inp = data.get("input", [])
    if isinstance(inp, str):
        messages.append({"role": "user", "content": inp})
    elif isinstance(inp, list):
        # 收集连续的 function_call 项，合并为一条 assistant.tool_calls 消息
        pending_tool_calls: list = []

        def _flush_tool_calls() -> None:
            if pending_tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": list(pending_tool_calls),
                })
                pending_tool_calls.clear()

        for item in inp:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type", "")
            role = item.get("role", "")

            if item_type == "function_call":
                # Responses API function_call → assistant message tool_calls
                pending_tool_calls.append({
                    "id": item.get("call_id") or item.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": item.get("name", ""),
                        "arguments": item.get("arguments", "{}"),
                    },
                })

            elif item_type == "function_call_output":
                # 先落盘积累的 function_call
                _flush_tool_calls()
                # Responses API function_call_output → tool role message
                messages.append({
                    "role": "tool",
                    "tool_call_id": item.get("call_id", ""),
                    "content": item.get("output", ""),
                })

            elif role in ("user", "assistant", "system", "developer", "tool"):
                # 普通消息
                _flush_tool_calls()
                content = _extract_content_parts(item.get("content", ""))
                msg: dict = {"role": role, "content": content}
                # 保留 assistant 消息中的 name 字段（GLM 支持）
                if role == "assistant" and item.get("name"):
                    msg["name"] = item["name"]
                messages.append(msg)

            elif item_type in ("message", ""):
                # 没有 role 时，根据 type 推断或默认 user
                _flush_tool_calls()
                content = _extract_content_parts(item.get("content", ""))
                messages.append({"role": "user", "content": content})

        # 循环后清空残留
        _flush_tool_calls()

    out["messages"] = messages
    return out


def _chat_to_responses_body(data: dict) -> dict:
    """
    Chat Completions 响应体 → Responses API 响应体（非流式）。

    ┌──────────────────────────────────────────────────────────────┐
    │ Chat Completions 字段                → Responses API 字段    │
    ├──────────────────────────────────────────────────────────────┤
    │ choices[0].finish_reason             → stop_reason + status  │
    │   "stop" / "eos"                     → "end_turn"            │
    │   "length" / "max_tokens"            → "max_tokens"          │
    │   "tool_calls" / "function_call"     → "tool_calls"          │
    │   "content_filter" / "sensitive"     → "content_filter"      │
    │ message.reasoning_content (GLM-Z1)   → reasoning output item │
    │ message.reasoning (DeepSeek-R1)      → reasoning output item │
    │ message.content                      → message output item   │
    │ message.tool_calls                   → function_call items   │
    │ usage.completion_tokens_details      → output_tokens_details │
    │   .reasoning_tokens (GLM-Z1)         → .reasoning_tokens     │
    │ usage.prompt_tokens_details          → input_tokens_details  │
    │   .cached_tokens                     → .cached_tokens        │
    │ id / request_id                      → resp_id               │
    └──────────────────────────────────────────────────────────────┘
    """
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    text = message.get("content") or ""
    # GLM-Z1 用 reasoning_content，DeepSeek-R1 用 reasoning
    reasoning = (message.get("reasoning_content")
                 or message.get("reasoning")
                 or "")
    tool_calls = message.get("tool_calls") or []
    usage = data.get("usage") or {}
    finish_reason = choice.get("finish_reason") or "stop"

    # finish_reason → stop_reason + status
    stop_reason = _FINISH_TO_STOP.get(finish_reason, "end_turn")
    if finish_reason in ("length", "max_tokens"):
        status = "incomplete"
        incomplete_details: Optional[dict] = {"reason": "max_output_tokens"}
    elif finish_reason in ("content_filter", "sensitive"):
        status = "incomplete"
        incomplete_details = {"reason": "content_filter"}
    else:
        status = "completed"
        incomplete_details = None

    # 构造响应 ID（兼容 GLM request_id）
    rid = data.get("id") or data.get("request_id") or ""
    resp_id = (
        f"resp_{rid}" if rid and not rid.startswith("resp_") else
        (rid or f"resp_{int(time.time())}")
    )

    output: list = []

    # 1. reasoning → reasoning output item（GLM-Z1 / DeepSeek）
    if reasoning:
        output.append({
            "id": "rs_001",
            "type": "reasoning",
            "status": "completed",
            "summary": [{"type": "summary_text", "text": reasoning}],
        })

    # 2. text content → message output item
    if text or not tool_calls:
        output.append({
            "id": "msg_001",
            "type": "message",
            "role": "assistant",
            "status": status,
            "content": [{"type": "output_text", "text": text, "annotations": []}],
        })

    # 3. tool_calls → function_call output items
    for tc in tool_calls:
        fn = tc.get("function") or {}
        tc_id = tc.get("id") or f"call_{len(output)}"
        output.append({
            "type": "function_call",
            "id": tc_id,
            "call_id": tc_id,
            "name": fn.get("name", ""),
            "arguments": fn.get("arguments", "{}"),
            "status": "completed",
        })

    # usage 字段（兼容 GLM completion_tokens_details / prompt_tokens_details）
    comp_details = usage.get("completion_tokens_details") or {}
    prompt_details = usage.get("prompt_tokens_details") or {}
    reasoning_tokens = comp_details.get("reasoning_tokens", 0)
    cached_tokens = prompt_details.get("cached_tokens", 0)

    return {
        "id": resp_id,
        "object": "response",
        "created_at": data.get("created", int(time.time())),
        "status": status,
        "model": data.get("model", ""),
        "output": output,
        "stop_reason": stop_reason,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "input_tokens_details": {"cached_tokens": cached_tokens},
            "output_tokens_details": {"reasoning_tokens": reasoning_tokens},
        },
        "error": None,
        "incomplete_details": incomplete_details,
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
    """生成一条 SSE 事件字节"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


async def _responses_stream_adapter(
    source: AsyncIterator[bytes],
) -> AsyncIterator[bytes]:
    """
    Chat Completions SSE 流 → Responses API SSE 事件流。

    ┌──────────────────────────────────────────────────────────────┐
    │ 处理的 delta 字段:                                            │
    │   delta.content              → response.output_text.delta   │
    │   delta.reasoning_content    → response.reasoning_summary_  │
    │   delta.reasoning (GLM 别名) →   text.delta                  │
    │   delta.tool_calls           → response.function_call_       │
    │                                   arguments.delta            │
    │   finish_reason              → stop_reason (response.done)  │
    │   usage / extra.usage (GLM)  → response.done usage          │
    └──────────────────────────────────────────────────────────────┘
    """
    resp_id = f"resp_{int(time.time())}"
    item_id = "msg_001"
    model = ""
    full_text = ""
    full_reasoning = ""
    usage: dict = {}
    stop_reason = "end_turn"

    started = False
    reasoning_started = False
    text_started = False
    text_output_index = 0

    # {stream_index: {id, item_id, name, arguments, output_index}}
    tool_calls_map: dict = {}
    next_output_index = 0

    buf = b""

    async for raw in source:
        buf += raw
        # 兼容 \n\n 与 \r\n\r\n 两种 SSE 块分隔符
        while True:
            if b"\n\n" in buf:
                block, buf = buf.split(b"\n\n", 1)
            elif b"\r\n\r\n" in buf:
                block, buf = buf.split(b"\r\n\r\n", 1)
            else:
                break

            for line in block.splitlines():
                line = line.strip()
                if not line.startswith(b"data:"):
                    continue
                payload = line[5:].strip().decode("utf-8", errors="replace")

                # ── [DONE] 收尾 ─────────────────────────────────────────
                if payload == "[DONE]":
                    # 关闭 reasoning 项
                    if reasoning_started:
                        yield _sse("response.reasoning_summary_text.done", {
                            "type": "response.reasoning_summary_text.done",
                            "item_id": "rs_001", "output_index": 0,
                            "summary_index": 0, "text": full_reasoning,
                        })
                        yield _sse("response.reasoning_summary_part.done", {
                            "type": "response.reasoning_summary_part.done",
                            "item_id": "rs_001", "output_index": 0, "summary_index": 0,
                            "part": {"type": "summary_text", "text": full_reasoning},
                        })
                        yield _sse("response.output_item.done", {
                            "type": "response.output_item.done", "output_index": 0,
                            "item": {
                                "id": "rs_001", "type": "reasoning", "status": "completed",
                                "summary": [{"type": "summary_text", "text": full_reasoning}],
                            },
                        })

                    # 关闭文本消息项
                    if text_started:
                        yield _sse("response.output_text.done", {
                            "type": "response.output_text.done",
                            "item_id": item_id, "output_index": text_output_index,
                            "content_index": 0, "text": full_text,
                        })
                        yield _sse("response.content_part.done", {
                            "type": "response.content_part.done",
                            "item_id": item_id, "output_index": text_output_index,
                            "content_index": 0,
                            "part": {"type": "output_text", "text": full_text, "annotations": []},
                        })
                        yield _sse("response.output_item.done", {
                            "type": "response.output_item.done",
                            "output_index": text_output_index,
                            "item": {
                                "id": item_id, "type": "message", "role": "assistant",
                                "status": "completed",
                                "content": [{"type": "output_text", "text": full_text,
                                             "annotations": []}],
                            },
                        })
                    elif not tool_calls_map:
                        # 无文本也无工具调用（空响应），补一个空消息项
                        yield _sse("response.output_item.done", {
                            "type": "response.output_item.done",
                            "output_index": text_output_index,
                            "item": {
                                "id": item_id, "type": "message", "role": "assistant",
                                "status": "completed",
                                "content": [{"type": "output_text", "text": "", "annotations": []}],
                            },
                        })

                    # 关闭所有 tool_call 项
                    for tc in sorted(tool_calls_map.values(), key=lambda x: x["output_index"]):
                        yield _sse("response.function_call_arguments.done", {
                            "type": "response.function_call_arguments.done",
                            "item_id": tc["item_id"],
                            "output_index": tc["output_index"],
                            "call_id": tc["id"],
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        })
                        yield _sse("response.output_item.done", {
                            "type": "response.output_item.done",
                            "output_index": tc["output_index"],
                            "item": {
                                "type": "function_call",
                                "id": tc["id"], "call_id": tc["id"],
                                "name": tc["name"], "arguments": tc["arguments"],
                                "status": "completed",
                            },
                        })

                    # 构建 response.done output 列表
                    done_output: list = []
                    if reasoning_started:
                        done_output.append({
                            "id": "rs_001", "type": "reasoning", "status": "completed",
                            "summary": [{"type": "summary_text", "text": full_reasoning}],
                        })
                    if text_started:
                        done_output.append({
                            "id": item_id, "type": "message", "role": "assistant",
                            "status": "completed",
                            "content": [{"type": "output_text", "text": full_text,
                                         "annotations": []}],
                        })
                    elif not tool_calls_map:
                        done_output.append({
                            "id": item_id, "type": "message", "role": "assistant",
                            "status": "completed",
                            "content": [{"type": "output_text", "text": "", "annotations": []}],
                        })
                    for tc in sorted(tool_calls_map.values(), key=lambda x: x["output_index"]):
                        done_output.append({
                            "type": "function_call",
                            "id": tc["id"], "call_id": tc["id"],
                            "name": tc["name"], "arguments": tc["arguments"],
                            "status": "completed",
                        })

                    # usage 字段
                    comp_details = usage.get("completion_tokens_details") or {}
                    prompt_details = usage.get("prompt_tokens_details") or {}

                    yield _sse("response.done", {
                        "type": "response.done",
                        "response": {
                            "id": resp_id, "object": "response",
                            "status": "completed",
                            "stop_reason": stop_reason,
                            "model": model, "created_at": int(time.time()),
                            "output": done_output,
                            "usage": {
                                "input_tokens": usage.get("prompt_tokens", 0),
                                "output_tokens": usage.get("completion_tokens", 0),
                                "total_tokens": usage.get("total_tokens", 0),
                                "input_tokens_details": {
                                    "cached_tokens": prompt_details.get("cached_tokens", 0),
                                },
                                "output_tokens_details": {
                                    "reasoning_tokens": comp_details.get("reasoning_tokens", 0),
                                },
                            },
                        },
                    })
                    yield b"data: [DONE]\n\n"
                    return

                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                # 第一个有效 chunk → response.created
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
                    started = True

                # usage 字段（部分后端在非 DONE chunk 里提前携带）
                if chunk.get("usage"):
                    usage = chunk["usage"]
                # GLM extra.usage 扩展字段
                extra_usage = (chunk.get("extra") or {}).get("usage")
                if extra_usage:
                    usage = extra_usage

                choices = chunk.get("choices") or []
                if not choices:
                    continue

                choice0 = choices[0]
                delta = choice0.get("delta") or {}
                finish_reason = choice0.get("finish_reason") or ""

                # finish_reason → stop_reason（在 [DONE] 之前的最后一个 chunk 里）
                if finish_reason:
                    stop_reason = _FINISH_TO_STOP.get(finish_reason, "end_turn")

                # ── Reasoning（GLM-Z1: reasoning_content；DeepSeek-R1: reasoning）──
                reasoning_delta = (delta.get("reasoning_content")
                                   or delta.get("reasoning")
                                   or "")
                if reasoning_delta:
                    if not reasoning_started:
                        yield _sse("response.output_item.added", {
                            "type": "response.output_item.added",
                            "output_index": next_output_index,
                            "item": {"id": "rs_001", "type": "reasoning",
                                     "status": "in_progress", "summary": []},
                        })
                        yield _sse("response.reasoning_summary_part.added", {
                            "type": "response.reasoning_summary_part.added",
                            "item_id": "rs_001", "output_index": next_output_index,
                            "summary_index": 0,
                            "part": {"type": "summary_text", "text": ""},
                        })
                        next_output_index += 1
                        reasoning_started = True
                    full_reasoning += reasoning_delta
                    yield _sse("response.reasoning_summary_text.delta", {
                        "type": "response.reasoning_summary_text.delta",
                        "item_id": "rs_001", "output_index": next_output_index - 1,
                        "summary_index": 0, "delta": reasoning_delta,
                    })

                # ── 普通文本 ───────────────────────────────────────────────
                content_delta = delta.get("content") or ""
                if content_delta:
                    if not text_started:
                        text_output_index = next_output_index
                        next_output_index += 1
                        yield _sse("response.output_item.added", {
                            "type": "response.output_item.added",
                            "output_index": text_output_index,
                            "item": {"id": item_id, "type": "message", "role": "assistant",
                                     "content": [], "status": "in_progress"},
                        })
                        yield _sse("response.content_part.added", {
                            "type": "response.content_part.added",
                            "item_id": item_id, "output_index": text_output_index,
                            "content_index": 0,
                            "part": {"type": "output_text", "text": "", "annotations": []},
                        })
                        text_started = True
                    full_text += content_delta
                    yield _sse("response.output_text.delta", {
                        "type": "response.output_text.delta",
                        "item_id": item_id, "output_index": text_output_index,
                        "content_index": 0, "delta": content_delta,
                    })

                # ── Tool calls delta ───────────────────────────────────────
                for tc_delta in (delta.get("tool_calls") or []):
                    tc_idx = tc_delta.get("index", 0)
                    if tc_idx not in tool_calls_map:
                        tc_id = tc_delta.get("id") or f"call_{tc_idx}"
                        tc_item_id = f"fc_{tc_id}"
                        tc_out_idx = next_output_index
                        next_output_index += 1
                        tc_name = (tc_delta.get("function") or {}).get("name", "")
                        tool_calls_map[tc_idx] = {
                            "id": tc_id, "item_id": tc_item_id,
                            "name": tc_name,
                            "arguments": "", "output_index": tc_out_idx,
                        }
                        yield _sse("response.output_item.added", {
                            "type": "response.output_item.added",
                            "output_index": tc_out_idx,
                            "item": {
                                "type": "function_call",
                                "id": tc_id, "call_id": tc_id,
                                "name": tc_name, "arguments": "",
                                "status": "in_progress",
                            },
                        })

                    tc_state = tool_calls_map[tc_idx]
                    fn_chunk = tc_delta.get("function") or {}

                    # name 可能在后续 chunk 补全
                    fn_name = fn_chunk.get("name", "")
                    if fn_name and not tc_state["name"]:
                        tc_state["name"] = fn_name

                    # arguments 增量拼接
                    args_delta = fn_chunk.get("arguments", "")
                    if args_delta:
                        tc_state["arguments"] += args_delta
                        yield _sse("response.function_call_arguments.delta", {
                            "type": "response.function_call_arguments.delta",
                            "item_id": tc_state["item_id"],
                            "output_index": tc_state["output_index"],
                            "call_id": tc_state["id"],
                            "delta": args_delta,
                        })


def _log_request(body: bytes, local_path: str) -> None:
    """打印已转换后的 Chat Completions 请求体摘要"""
    if not body:
        return
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return
    model = data.get("model", "-")
    messages = data.get("messages") or []
    tools = data.get("tools") or []
    resp_fmt = data.get("response_format")

    logger.info("  path=%s  model=%s  messages=%d  tools=%d%s",
                local_path, model, len(messages), len(tools),
                f"  response_format={resp_fmt['type']}" if resp_fmt else "")

    for i, msg in enumerate(messages[:10]):  # 最多打 10 条
        role = msg.get("role", "?")
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls")
        if tool_calls:
            names = [tc.get("function", {}).get("name", "?") for tc in tool_calls]
            logger.info("  [%d] %s: <tool_calls: %s>", i, role, ", ".join(names))
            continue
        if isinstance(content, list):
            text = " ".join(
                p.get("text", "") for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            )
        else:
            text = str(content or "")
        preview = text[:200].replace("\n", "\\n")
        if len(text) > 200:
            preview += f"…(+{len(text) - 200})"
        logger.info("  [%d] %s: %s", i, role, preview)

    if len(messages) > 10:
        logger.info("  ... (%d 条消息未显示)", len(messages) - 10)


# ── 代理核心路由 ──────────────────────────────────────────────
async def _proxy_handler(request: Request, local_path: str) -> Response:
    is_responses = (local_path == "/v1/responses")

    # 1. 获取 Token
    token = await token_manager.get_token()

    # 2. 目标 URL（直接使用完整配置地址，不拼接路径）
    target_url = TARGET_API_URL
    if request.url.query:
        target_url += f"?{request.url.query}"

    # 3. 请求头
    forward_headers = _build_forward_headers(request, token)

    # 4. 读取请求体
    body = await request.body()
    original_body = body

    # 5. /v1/responses → 转换为 Chat Completions 格式
    if is_responses and body:
        try:
            req_data = json.loads(body)
            logger.info("  [RAW Responses API REQUEST]\n%s",
                        json.dumps(req_data, ensure_ascii=False, indent=2))
            chat_data = _responses_to_chat_body(req_data)
            body = json.dumps(chat_data, ensure_ascii=False).encode("utf-8")
            forward_headers["content-type"] = "application/json"
            forward_headers["content-length"] = str(len(body))
            logger.info("  [CONVERTED Chat Completions REQUEST]\n%s",
                        json.dumps(chat_data, ensure_ascii=False, indent=2))
        except Exception as exc:
            logger.warning("  [responses→chat] 转换失败，原样转发: %s", exc)
            logger.warning("  [RAW REQUEST bytes] %s", original_body[:500])

    # 6. 检测是否流式
    is_stream = _detect_stream(body)

    logger.info(
        "→ %s %s → %s | stream=%s | body=%d bytes",
        request.method, local_path, target_url, is_stream, len(body),
    )
    logger.info("  [FORWARD HEADERS] %s",
                {k: v for k, v in forward_headers.items()
                 if k.lower() not in (AUTH_HEADER_NAME.lower(), "authorization")})
    _log_request(body, local_path)

    # 7. 转发
    if is_stream:
        if is_responses:
            return _stream_responses_response(request.method, target_url, forward_headers, body)
        return await _proxy_stream(request.method, target_url, forward_headers, body)

    resp = await _proxy_normal(request.method, target_url, forward_headers, body)

    # 打印响应体
    try:
        resp_text = resp.body.decode("utf-8", errors="replace")
        logger.info("  [RESPONSE %d] %s", resp.status_code, resp_text[:3000])
    except Exception:
        pass

    # 8. /v1/responses 非流式：将 Chat Completions 响应转回 Responses API 格式
    if is_responses and resp.status_code == 200:
        try:
            chat_resp = json.loads(resp.body)
            responses_resp = _chat_to_responses_body(chat_resp)
            logger.info("  [chat→responses] 响应转换完成，stop_reason=%s",
                        responses_resp.get("stop_reason"))
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
    """流式 /v1/responses：Chat SSE 流 → Responses API SSE 事件流"""

    async def _gen():
        async def _chat_chunks() -> AsyncIterator[bytes]:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0),
                follow_redirects=True, verify=False, trust_env=False,
            ) as client:
                async with client.stream(method=method, url=url,
                                         headers=headers, content=body) as resp:
                    logger.info("← %d (stream/responses) %s", resp.status_code, url)
                    async for chunk in resp.aiter_bytes(chunk_size=512):
                        if chunk:
                            yield chunk

        async for event_bytes in _responses_stream_adapter(_chat_chunks()):
            yield event_bytes

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── 路由注册 ─────────────────────────────────────────────────
@app.api_route(
    "/v1/chat/completions",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
)
async def chat_completions(request: Request) -> Response:
    return await _proxy_handler(request, "/v1/chat/completions")


@app.api_route(
    "/v1/responses",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
)
async def responses(request: Request) -> Response:
    return await _proxy_handler(request, "/v1/responses")


async def _proxy_normal(method: str, url: str, headers: dict, body: bytes) -> Response:
    """转发普通（非流式）请求"""
    async with httpx.AsyncClient(
        timeout=120.0, follow_redirects=True, verify=False, trust_env=False,
    ) as client:
        resp = await client.request(method=method, url=url, headers=headers, content=body)

    logger.info("← %d %s", resp.status_code, url)
    if resp.status_code >= 400:
        logger.error("  [ERROR RESPONSE %d] headers=%s body=%s",
                     resp.status_code, dict(resp.headers), resp.text[:2000])

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=_build_resp_headers(resp),
        media_type=resp.headers.get("content-type"),
    )


async def _proxy_stream(method: str, url: str, headers: dict, body: bytes) -> StreamingResponse:
    """转发流式（SSE）请求，逐块直传"""

    async def _chunk_generator():
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0),
            follow_redirects=True, verify=False, trust_env=False,
        ) as client:
            async with client.stream(method=method, url=url,
                                     headers=headers, content=body) as resp:
                logger.info("← %d (stream) %s", resp.status_code, url)
                async for chunk in resp.aiter_bytes(chunk_size=512):
                    if chunk:
                        yield chunk

    return StreamingResponse(
        _chunk_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── 健康检查 ─────────────────────────────────────────────────
@app.get("/_proxy/health")
async def health() -> dict:
    has_token = token_manager._token is not None
    age = int(time.monotonic() - token_manager._last_refresh) if has_token else -1
    return {
        "status": "ok",
        "version": "2.0.0",
        "has_token": has_token,
        "skip_token_auth": SKIP_TOKEN_AUTH,
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
        access_log=False,
    )
