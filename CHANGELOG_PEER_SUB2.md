# CHANGELOG — Peer Sub2 Runtime Failover

## 2026-07-19 — G2A ↔ Sub2 运行时自动调配（peer）

### 功能
- G2A 本地账号池限流/耗尽/上游失败时，可自动转发到对端 Sub2API（`/v1/chat/completions`）。
- 与「SUB2导入 / A2G导入」账号互通互补：导入是静态合池，peer 是运行时灵活调配。

### 配置（`data/config.toml`）
```toml
[peer]
sub2_enabled = true
sub2_base_url = "http://127.0.0.1:8080"
sub2_api_key = "<Sub2 API Key>"
prefer_local_first = true
timeout_seconds = 90
models = ["grok-4.5", "grok-4"]
on_status_codes = [429, 503, 502, 401, 403]
```

### 行为
- 默认 `prefer_local_first=true`：先本地池，失败再 peer。
- 触发：`RateLimitError`、指定状态码的 `UpstreamError`、no available 类错误。
- 防递归：请求头 `X-Peer-Failover` / `X-G2A-Peer-Failover` = 1 时不再二次 peer。
- 成功响应可从日志看到 `peer.sub2.*`。

### 文件
- `app/products/openai/peer_sub2.py`（新建）
- `console_chat.py` / `chat.py` / `router.py` 接入

### 端口说明
- 启动脚本优先 8010；若 8010 被旧进程占用则用 8012。两者同一套代码与库。