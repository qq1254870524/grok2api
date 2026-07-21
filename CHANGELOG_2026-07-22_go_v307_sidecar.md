# 2026-07-22 Go v3.0.7 旁路大升级（不替换 8010）

生产 Python 8010 保持全部本地改动。
旁路 Go：`C:\Users\zhang\grok-regkit-services1\grok2api-v3` 端口 8020。
详见该目录 `LOCAL_CUSTOMIZATIONS.md` 与包 `packages/stable-2026-07-22-g2a-go-v307-local-bridge`。

## 收尾状态 2026-07-22

- 号池迁移完成：Python active 3746 -> Go v3 `grok_web` total/available **3746**
- regkit 兼容桥 `127.0.0.1:8011` 已启动；修复列表 `provider=grok_web`
- bridge 冒烟：`/health` ok；`/admin/api/tokens` total=3746
- 生产 8010 peer Sub2 定制保留；未切生产到 8020
- GitHub 包名：`stable-2026-07-22-g2a-go-v307-local-bridge`（不覆盖 18r40/41/42）
