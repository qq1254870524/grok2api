# 2026-07-21 grok2api 双轨发版

## 背景

并行按用户要求把本地 grok2api 对齐 https://github.com/chenyme/grok2api 最新版，同时**保留本地改动**。

核查结果：上游自 **v3.0.0** 起已从 Python 重写为 **Go + React**（当前 **v3.0.7** `11bb5e2`）。
本地生产是 **Python 2.0.4.rc4** + Sub2/peer 定制，与 Go 无共同可 merge 的业务层（甚至无 merge-base 可用）。

## 决策

1. **生产轨道（保留全部本地改动）**：Python `v2.0.4.rc4` + peer_sub2 + SUB2 导入 + start_g2a + grok-4.5 别名  
   包名：`stable-2026-07-22-g2a-python-204rc4-peer-sub2`
2. **上游最新轨道（评估）**：chenyme Go `v3.0.7` 纯净快照  
   包名：`stable-2026-07-22-g2a-upstream-go-v307`
3. **不覆盖**历史 packages / 旧 release
4. **不热替换**正在运行的 8010 Python 进程与 `.venv`/`data`

## 本地定制清单（生产轨道）

- peer runtime failover → Sub2API
- Admin SUB2 import from Sub2API + SSO dedupe (no overwrite)
- account.html + i18n
- config.defaults.toml peer/sub2 keys
- start_g2a.ps1
- grok-4.5 model aliases
- related CHANGELOG_* 文档

## 后续（未在本包完成）

- 将 Sub2 导入 / peer failover 移植到 Go v3.0.7 管理 API
- regkit 对接适配 Go admin JWT 与账号模型
- 完成移植后再切换生产 8010

## 验证

- 本地 8010 仍由 Python granian 提供服务
- 包目录存在且 SHA256 已生成
- 旧 18r* / 旧 g2a packages 未删除
