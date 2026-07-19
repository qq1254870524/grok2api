# Changelog — Grok2API SUB2 Import (2026-07-19)

## stable-2026-07-19-g2a-sub2-import

### Highlights
- **Sub2API ↔ Grok2API 账号池互通（手动双向导入）**
  - Grok2API 管理端新增 **「SUB2导入」**：从 Sub2API 导出导入 SSO 到本机号池。
  - Sub2API 侧对应 **「A2G导入」**（见 sub2api 仓库 fork2）。
  - 去重键为规范化 SSO（`_sanitize` 剥离 `sso=` 等）；**已存在 token 一律跳过，不覆盖**额度/状态。

### Backend
- 新增 `POST /tokens/import/sub2`（`app/products/web/admin/tokens.py`）
  - 请求体：`content` / `contents` / `tokens` / `sso_tokens` + `pool` + `tags`
  - 解析：
    - Sub2API `type=sub2api-data`：`accounts[].credentials.sso|sso_token|...`（仅 platform=grok/xai 或未标 platform）
    - G2A 风格 `{basic:[...], super:[...]}` pool JSON
    - 纯文本每行一个 SSO
  - 与 `/tokens/add` 相同策略：已存在 active token **skipped / never overwrite**
  - 可选 `auto_nsfw`：导入后异步刷新额度并可选开启 NSFW

### Frontend / i18n
- `app/statics/admin/account.html`
  - 页头按钮 **SUB2导入**
  - 弹窗：文件 + 粘贴 + 号池类型 + 自动 NSFW
- i18n：`zh.json` / `en.json`（及其他语言默认英文键）`account.sub2Import*` / `actionSub2Import*`

### 使用流程（双向）
1. **G2A → Sub2API（A2G）**  
   Grok2API 导出 txt/JSON → Sub2API 账户页「A2G导入」→ SSO→OAuth 创建，重复 SSO 跳过。
2. **Sub2API → G2A（SUB2）**  
   Sub2API 数据导出（需 Grok 账号带 `credentials.sso`）→ Grok2API「SUB2导入」→ 写入号池，重复 SSO 跳过。

### Notes
- 手动操作，不做自动同步。
- 旧 Sub2API Grok 账号若从未写入 `sso` 字段，无法从导出还原到 G2A。
- 不覆盖既有 GitHub release；本 tag 为增量能力包。

### Verification
- Python 语法检查：`tokens.py` OK
- SSO 提取单测：txt / sub2api-data / pool JSON 解析与 openai 平台过滤 OK
