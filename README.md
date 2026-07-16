🚀 IceHost 代理智能续期（GitHub Actions）

这是一个基于 GitHub Actions + Playwright + SeleniumBase 的自动化脚本，用于定时登录 IceHost 控制面板，自动点击续期按钮，并通过 Hysteria2 代理解决网络阻断问题，配合本地 Cookie 缓存机制，实现近乎无人值守的自动续期。

⚠️ **注意**：由于网站可能存在防护盾（CF盾等），部分质量较差的机房节点可能无法通过验证，建议自行准备相对干净的代理节点或使用脚本内置的 Hysteria2 代理配置。

━━━━━━━━━━━━━━━━━━━━━━

🔐 Secrets 配置说明

在 GitHub 仓库的 `Settings ➡ Secrets and variables ➡ Actions` 中添加以下密钥：

| Secret 名称 | 是否必填 | 说明 |
| :--- | :---: | :--- |
| `PTERODACTYL_EMAIL` | ✅ **必填** | IceHost 面板的登录账号（邮箱） |
| `PTERODACTYL_PASSWORD` | ✅ **必填** | IceHost 面板的登录密码 |
| `TG_TOKEN` | ❌ 可选 | Telegram Bot Token（用于发送续期结果截图和通知） |
| `TG_CHAT_ID` | ❌ 可选 | Telegram Chat ID（接收通知的用户或群组 ID） |

━━━━━━━━━━━━━━━━━━━━━━

📦 部署步骤

1. **Fork 本项目** 到您自己的 GitHub 账号下。
2. 在 GitHub 仓库页面，点击 **Actions** 菜单，点击 `I understand my workflows, go ahead and enable them` 以允许工作流运行。
3. 进入仓库的 **Settings ➡ Secrets and variables ➡ Actions**，点击 **New repository secret**，依次添加上方“必填”及您需要的“可选” Secrets。
4. **手动测试运行**：点击 **Actions** 菜单，选择左侧的 `IceHost 代理智能续期` 工作流，点击右侧的 `Run workflow` 按钮手动触发一次，检查日志是否执行成功。
5. **调整定时运行时间**：根据需要，修改 `.github/workflows/renew.yml` 文件中的 `cron` 时间（默认每 2 小时运行一次）。

━━━━━━━━━━━━━━━━━━━━━━

📁 Cookie 持久化机制说明

本脚本包含一套自动重试与 Cookie 保存机制，防止频繁因登录验证导致失败：

1. **优先使用缓存**：脚本运行时会读取仓库中的 `session_cookies.json` 文件，尝试使用缓存的会话状态直接访问续期页面。
2. **自动失效检测**：如果发现 Cookie 过期（页面跳转回登录页），脚本会自动暂停 Playwright，拉起 **SeleniumBase** 使用您配置的邮箱和密码进行模拟登录。
3. **自动更新缓存**：重新登录成功后，脚本会自动获取最新的 Cookie，覆写并提交 `session_cookies.json` 文件到您的 GitHub 仓库。
4. **永久运行**：后续 Actions 执行时，将直接使用最新更新的 Cookie 免密续期，大大减少触发账号保护机制的概率。

━━━━━━━━━━━━━━━━━━━━━━

⚠️ 注意事项与修改指南

* **代理配置（核心）**：脚本内置了 `HY2_URL` 和 `HY2_AUTH` 的 Hysteria2 代理配置。**请不要将这些敏感信息通过明文写在代码中，建议参考脚本代码修改为从环境变量读取，或者您自己替换为有效的代理配置。**
* **环境依赖**：Actions 运行环境已通过 `cache` 缓存了 Playwright 和 Python 虚拟环境，因此后续运行速度会大幅提升（无需每次都重新下载浏览器核心）。
* **按钮文本匹配**：如果 IceHost 面板的续期按钮文案发生改变，请前往 `main.py` 中找到 `RENEW_BUTTON_TEXT` 变量，将其值更新为新的按钮文字（如“DODAJ 6 GODZIN WAŻNOŚCI”）。
* **日志清理**：工作流脚本包含自动清理旧运行记录的步骤（`WORKFLOW_CLEAN_TOKEN` 为可选，已做错误跳过处理），会根据时间自动清理 Git 仓库中的旧记录，防止仓库容量膨胀。
* **服务稳定性**：自动续期依赖于您提供代理节点的稳定性，如节点无法连接，会导致脚本无法加载页面。请定期检查 Actions 的 Telegram 通知或运行日志。
