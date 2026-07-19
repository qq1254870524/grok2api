# CHANGELOG

## 2026-07-19 — stable-2026-07-19-peer-sub2

### Highlights
- **G2A ↔ Sub2 运行时 peer 自动调配**：本地号池 429/无号/上游失败时，自动转发到 Sub2API /v1/chat/completions。
- 与「SUB2导入」账号互通互补：导入合池 + 运行时 peer。
- 启动脚本 start_g2a.ps1 优先 **8010**，被占时回退 **8012**（同一套代码与库）。

### Peer Sub2
- 新文件：pp/products/openai/peer_sub2.py
- 接入：chat.py / console_chat.py / 
outer.py
- 默认配置见 config.defaults.toml [peer]：
  - sub2_enabled / sub2_base_url / sub2_api_key
  - prefer_local_first=true
  - on_status_codes 含 429/5xx/401/403
- 防递归：X-Peer-Failover / X-G2A-Peer-Failover
- 详见 [CHANGELOG_PEER_SUB2.md](./CHANGELOG_PEER_SUB2.md)

### SUB2 导入（已有能力回顾）
- 管理页「SUB2导入」：服务端拉取 Sub2 export/g2a-sso
- SSO 去重 skip，不覆盖
- Admin 鉴权用 **app_key**

### 端口说明
- 正常：http://127.0.0.1:8010
- 8010 被 portproxy/幽灵进程占用时用 8012；**不要把 8010 再做 portproxy 转发到别的端口**，会导致 granian bind 10013

### Notes
- 不覆盖既有 tag/release。
- 新 tag：stable-2026-07-19-peer-sub2

﻿# CHANGELOG

## 2026-07-19 — stable-2026-07-19-docs-sync-18r28i

- Companion restore marker with grok-regkit 18r28i full-stack docs sync.
- Does not overwrite prior releases.
## 2026-07-18 — restore point #3 `stable-2026-07-18-matrix-uifallback`

- Tagged with regkit matrix/UI-fallback restore point #3 for coordinated rollback.
- Does not overwrite previous stable tags.

