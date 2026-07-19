# Changelog — G2A ↔ Sub2API direct bridge

## stable-2026-07-19-g2a-sub2-direct (2026-07-19)

### 新增 / 行为
- **网站直连导入（主路径）**：管理页「SUB2导入」填写 Sub2API Base URL + Admin Token，由 **G2A 服务端**拉取 `GET /api/v1/admin/accounts/export/g2a-sso`，无需手工导出文件。
- 请求体字段：`sub2_base_url`、`sub2_admin_token`（`POST /admin/api/tokens/import/sub2`）。
- 高级选项仍保留：文件 / 粘贴导入。

### 去重
- 已存在 SSO **一律 skip**，永不覆盖。
- 与既有 `/tokens/add` 策略一致。

### 本地部署说明
- 启动脚本：`start_g2a.ps1`（优先 8010；若 8010 被幽灵进程占用则自动 8012）。
- 若 OpenAPI 无 `sub2_base_url`，说明仍是旧进程：请用脚本重启，或打开 `http://127.0.0.1:8012/admin/account`。
- 浏览器强刷（Ctrl+F5）管理页以加载新静态资源。
- Admin 鉴权使用 **`app_key`**（管理后台登录密钥），不是 `api_key`。

### 与 Sub2 数量差异说明
- G2A 号池是 **SSO token** 列表。
- Sub2 Grok 账号多为 **OAuth 兑换**；历史账号可能无 `credentials.sso`，无法双向完整对齐。
- 导入时无 SSO / 兑换失败会 failed；重复 SSO/Email 会 skipped。

