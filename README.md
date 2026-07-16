# 🚀 IceHost 代理智能续期（GitHub Actions）

这是一个基于 GitHub Actions + Playwright + SeleniumBase 的自动化脚本，用于定时登录 IceHost 控制面板，自动点击续期按钮。脚本使用 Hysteria2 代理解决网络阻断，并配合本地 Cookie 缓存与自动重登录机制，实现无人值守的长期自动续期。

⚠️ **注意**：建议使用相对干净的代理节点，过于垃圾的机房 IP 可能会被网站的防护盾（如 CF 盾）拦截。

━━━━━━━━━━━━━━━━━━━━━━

## 🔐 Secrets 配置说明

在 GitHub 仓库的 `Settings ➡ Secrets and variables ➡ Actions` 中，点击 `New repository secret` 添加以下变量：

| Secret 名称 | 是否必填 | 说明 |
| :--- | :---: | :--- |
| `PTERODACTYL_EMAIL` | ✅ **必填** | IceHost 面板的登录账号（邮箱）。用于 Cookie 失效时重新登录。 |
| `PTERODACTYL_PASSWORD` | ✅ **必填** | IceHost 面板的登录密码。 |
| `PTERODACTYL_COOKIE` | ❌ **自动维护** | **无需手动添加**。脚本首次运行或失效后，会自动重新登录并将最新的 JSON 格式 Session Cookie 写入此 Secret。 |
| `TG_TOKEN` | ❌ 可选 | Telegram Bot Token（用于发送续期结果的截图与文字通知）。 |
| `TG_CHAT_ID` | ❌ 可选 | Telegram 接收通知的 Chat ID（个人 ID 或群组 ID）。 |
| `WORKFLOW_CLEAN_TOKEN` | ❌ 可选 | GitHub Personal Access Token (Classic)。用于脚本运行结束后自动清理旧的 Actions 运行记录，防止日志文件占用过多空间。 |

━━━━━━━━━━━━━━━━━━━━━━

## 📦 部署步骤

1. **Fork 本项目** 到您自己的 GitHub 账号下。
2. 在 GitHub 仓库页面，点击 **Actions** 菜单，点击 `I understand my workflows, go ahead and enable them` 以允许工作流运行。
3. 进入仓库的 **Settings ➡ Secrets and variables ➡ Actions**，点击 **New repository secret**，依次添加上方表格中的 **必填项**（`PTERODACTYL_EMAIL` 和 `PTERODACTYL_PASSWORD`），以及您需要的可选变量。
4. **手动测试运行**：点击 **Actions** 菜单，选择左侧的 `IceHost 代理智能续期` 工作流，点击右侧的 `Run workflow` 按钮手动触发一次，检查日志是否执行成功。
5. **调整定时运行时间**：根据实际续期需求，修改 `.github/workflows/renew.yml` 文件中的 `cron` 时间表达式（默认设置为每 2 小时运行一次）。

━━━━━━━━━━━━━━━━━━━━━━

## 🧠 核心机制说明

* **Cookie 持久化与自愈**：脚本运行时会优先读取 `PTERODACTYL_COOKIE` 缓存。如果发现 Cookie 过期，会自动触发备用机制，用 `PTERODACTYL_EMAIL` 和 `PASSWORD` 模拟登录，**登录成功后自动更新并保存新的 Cookie 到 Secrets 中**，实现闭环自愈，无需人工干预。
* **代理避风控**：脚本在 Playwright 和 SeleniumBase 中都配置了 SOCKS5 代理（`127.0.0.1:1080`），并在执行前启动 Hysteria2 客户端，防止 GitHub Actions 原生 IP 被拦截。
* **自动清理旧记录**：工作流末尾内置了日志清理脚本，配合 `WORKFLOW_CLEAN_TOKEN` 可自动删除历史运行记录，保持仓库整洁。

━━━━━━━━━━━━━━━━━━━━━━

