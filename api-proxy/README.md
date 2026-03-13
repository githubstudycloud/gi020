# API Proxy

将私有接口包装成 OpenAI 兼容格式的轻量代理，自动管理 Token。

## 工作原理

```
外部调用                        代理内部                        实际接口
─────────────────────────────────────────────────────────────────────
POST /v1/chat/completions  →  自动注入 Auth Token  →  POST TARGET_API_URL
POST /v1/responses         →  自动注入 Auth Token  →  POST TARGET_API_URL
                              (每30分钟自动刷新)
```

- 外部路径（`/v1/chat/completions`、`/v1/responses` 等）**不会拼接**到目标地址
- 所有请求统一转发到 `TARGET_API_URL` 这一个固定地址
- 外部若传了同名鉴权字段，会被内部 Token 强制覆盖

## 快速开始

**安装依赖**
```bash
pip install fastapi "uvicorn[standard]" httpx
```

**修改配置**（`proxy.py` 顶部配置区，或通过环境变量）

| 变量 | 说明 | 必改 |
|------|------|------|
| `TOKEN_API_URL` | 获取 Token 的接口地址 | ✅ |
| `TOKEN_PARAM_1_NAME` / `TOKEN_PARAM_1_VALUE` | 第一个登录参数 | ✅ |
| `TOKEN_PARAM_2_NAME` / `TOKEN_PARAM_2_VALUE` | 第二个登录参数 | ✅ |
| `TARGET_API_URL` | 实际对话接口完整地址（固定，不拼接路径） | ✅ |
| `AUTH_HEADER_NAME` | Token 注入的 Header 字段名，默认 `Auth` | 按需 |
| `LOCAL_API_PREFIX` | 对外暴露的路径前缀，默认 `/v1` | 按需 |
| `PROXY_PORT` | 监听端口，默认 `8080` | 按需 |

**启动**
```bash
python proxy.py
```

## 接口地址

| 路径 | 用途 |
|------|------|
| `POST /v1/chat/completions` | ChatGPT 对话格式 |
| `POST /v1/responses` | OpenAI Responses API 格式 |
| `GET  /_proxy/health` | 健康检查，查看 Token 状态 |

支持流式响应（请求体含 `"stream": true` 时自动切换 SSE）。

## 环境变量方式启动

```bash
export TOKEN_API_URL=https://your-api.com/auth/token
export TOKEN_PARAM_1_NAME=username
export TOKEN_PARAM_1_VALUE=admin
export TOKEN_PARAM_2_NAME=password
export TOKEN_PARAM_2_VALUE=secret
export TARGET_API_URL=https://your-api.com/api/chat/send
export AUTH_HEADER_NAME=Auth
export PROXY_PORT=8080

python proxy.py
```

## 在 litellm 中使用

```python
import litellm

response = litellm.completion(
    model="openai/your-model-name",
    base_url="http://localhost:8080",
    api_key="any",          # 代理不校验，随意填
    messages=[{"role": "user", "content": "hello"}],
)
```

详细部署（systemd / NSSM / Nginx）见 [DEPLOY.md](./DEPLOY.md)。
