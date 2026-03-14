import os
import asyncio
import requests
from playwright.async_api import async_playwright

def send_tg_msg(message):
    token = os.environ.get('TG_BOT_TOKEN')
    chat_id = os.environ.get('TG_CHAT_ID')
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": f"🤖 **IceHost 续期助手**\n\n{message}", "parse_mode": "Markdown"}
        try:
            requests.post(url, data=data, timeout=10)
        except:
            pass

async def run():
    async with async_playwright() as p:
        # 尝试启动浏览器
        browser = await p.chromium.launch(headless=True)
        # 模拟移动端，通常移动端的 Cloudflare 验证较弱
        context = await browser.new_context(
            viewport={'width': 390, 'height': 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            is_mobile=True,
            has_touch=True
        )
        page = await context.new_page()
        msg = ""

        try:
            print("正在前往登录页...")
            # 增加等待时间，处理可能的 Cloudflare 等待室
            response = await page.goto("https://dash.icehost.pl/login", timeout=90000, wait_until="load")
            
            # 停留 10 秒，让可能的 5 秒盾跑完
            await asyncio.sleep(10)

            # 检查是否依然被盾拦截
            title = await page.title()
            if "Just a moment" in title or "Cloudflare" in title:
                msg = "🛑 **拦截警告**：被 Cloudflare 五秒盾挡住了，脚本暂时无法进入。"
            else:
                # 尝试查找邮箱输入框，使用更宽松的定位
                email_field = page.locator('input[type="email"], input[name="email"]')
                
                # 等待输入框出现，延长到 45 秒
                await email_field.wait_for(state="visible", timeout=45000)
                
                await email_field.fill(os.environ['ICE_EMAIL'])
                await page.fill('input[type="password"]', os.environ['ICE_PASSWORD'])
                
                # 点击登录
                await page.click('button[type="submit"]')
                
                # 等待跳转到服务器页
                await asyncio.sleep(5)
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5", timeout=60000)
                
                # 寻找按钮
                renew_btn = page.get_by_text("增加6小时的有效期")
                if await renew_btn.is_visible():
                    await renew_btn.click()
                    await asyncio.sleep(3)
                    msg = "✅ **续期指令发送成功！**"
                else:
                    msg = "⚠️ **按钮未发现**：可能已在冷却中，或页面结构有变。"

        except Exception as e:
            msg = f"❌ **执行超时**：页面未能正常显示登录框。\n这通常是因为 IceHost 的防火墙拦截了 GitHub 的服务器。"
            print(f"Error: {e}")
        finally:
            send_tg_msg(msg)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
