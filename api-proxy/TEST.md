# 接口测试文档

代理服务启动后，使用以下方式验证各接口是否正常工作。

---

## 一、健康检查

```bash
curl http://localhost:8080/_proxy/health
```

预期响应：

```json
{
  "status": "ok",
  "has_token": true,
  "token_age_seconds": 42,
  "refresh_interval_seconds": 1800,
  "target": "https://your-api.com/api/chat/send",
  "local_paths": ["/v1/chat/completions", "/v1/responses"]
}
```

`has_token: true` 且无报错即表示服务正常、Token 已就绪。

---

## 二、/v1/chat/completions（Chat Completions 格式）

### 非流式

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model-name",
    "messages": [
      {"role": "user", "content": "你好，介绍一下你自己"}
    ]
  }'
```

预期响应（Chat Completions 格式）：

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "你好！我是..."},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
}
```

### 流式

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model-name",
    "messages": [
      {"role": "user", "content": "用三句话介绍春天"}
    ],
    "stream": true
  }'
```

预期响应（SSE 流）：

```
data: {"id":"chatcmpl-xxx","choices":[{"delta":{"role":"assistant"},"finish_reason":null}]}
data: {"id":"chatcmpl-xxx","choices":[{"delta":{"content":"春天"},"finish_reason":null}]}
data: {"id":"chatcmpl-xxx","choices":[{"delta":{"content":"是"},"finish_reason":null}]}
...
data: [DONE]
```

### 多轮对话

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model-name",
    "messages": [
      {"role": "system", "content": "你是一个简洁的助手，回答不超过20字"},
      {"role": "user",   "content": "1+1等于几"},
      {"role": "assistant", "content": "等于2。"},
      {"role": "user",   "content": "再加1呢"}
    ]
  }'
```

---

## 三、/v1/responses（Responses API 格式）

litellm 调用此接口时会自动走该格式。也可以直接测试。

### 非流式 — input 为字符串

```bash
curl http://localhost:8080/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model-name",
    "input": "用一句话解释什么是人工智能"
  }'
```

### 非流式 — input 为消息数组（标准格式）

```bash
curl http://localhost:8080/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model-name",
    "instructions": "你是一个简洁的助手",
    "input": [
      {
        "role": "user",
        "content": [{"type": "input_text", "text": "介绍一下Python语言"}]
      }
    ]
  }'
```

预期响应（Responses API 格式）：

```json
{
  "id": "resp_chatcmpl-xxx",
  "object": "response",
  "status": "completed",
  "model": "your-model-name",
  "output": [{
    "id": "msg_001",
    "type": "message",
    "role": "assistant",
    "status": "completed",
    "content": [{"type": "output_text", "text": "Python 是一门..."}]
  }],
  "usage": {"input_tokens": 15, "output_tokens": 30, "total_tokens": 45}
}
```

### 流式

```bash
curl http://localhost:8080/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model-name",
    "input": [
      {"role": "user", "content": [{"type": "input_text", "text": "数到5"}]}
    ],
    "stream": true
  }'
```

预期响应（Responses API SSE 事件流）：

```
event: response.created
data: {"type":"response.created","response":{"id":"resp_xxx","status":"in_progress",...}}

event: response.output_item.added
data: {"type":"response.output_item.added","output_index":0,"item":{...}}

event: response.content_part.added
data: {"type":"response.content_part.added","item_id":"msg_001",...}

event: response.output_text.delta
data: {"type":"response.output_text.delta","delta":"1","item_id":"msg_001",...}

event: response.output_text.delta
data: {"type":"response.output_text.delta","delta":"、2","item_id":"msg_001",...}

...

event: response.output_text.done
data: {"type":"response.output_text.done","text":"1、2、3、4、5",...}

event: response.output_item.done
data: {"type":"response.output_item.done",...}

event: response.done
data: {"type":"response.done","response":{"status":"completed",...}}

data: [DONE]
```

---

## 四、通过 litellm 测试

```python
import litellm

# 测试 chat completions 路径
resp = litellm.completion(
    model="openai/your-model-name",
    base_url="http://localhost:8080",
    api_key="any",
    messages=[{"role": "user", "content": "你好"}],
)
print(resp.choices[0].message.content)

# 测试 responses 路径（litellm 自动走 /v1/responses）
resp = litellm.responses(
    model="openai/your-model-name",
    base_url="http://localhost:8080",
    api_key="any",
    input="你好",
)
print(resp.output[0].content[0].text)
```

---

## 五、常见异常排查

| 现象 | 排查方向 |
|------|---------|
| `has_token: false` | Token 接口配置有误，查看 `proxy.log` 中的刷新日志 |
| 请求返回 `400` | 查看日志中 `[CONVERTED REQUEST BODY]` 和 `[ERROR RESPONSE 400]`，确认转换后格式是否符合目标接口要求 |
| 请求返回 `401` / `403` | Token 过期或字段名错误，检查 `AUTH_HEADER_NAME` 配置 |
| 流式响应无数据 | 检查 Nginx 是否配置了 `proxy_buffering off`；确认目标接口支持流式输出 |
| `/v1/responses` 返回 `output` 内容为空 | 查看日志 `[CONVERTED REQUEST BODY]` 中 messages 的 content 字段是否正确提取 |
| litellm 报连接错误 | 确认 `base_url` 不含路径（应为 `http://host:port`，不要加 `/v1`） |
