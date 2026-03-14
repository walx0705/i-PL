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
        requests.post(url, data=data, timeout=10)

def send_tg_photo(photo_path):
    token = os.environ.get('TG_BOT_TOKEN')
    chat_id = os.environ.get('TG_CHAT_ID')
    if token and chat_id and os.path.exists(photo_path):
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(photo_path, 'rb') as photo:
            requests.post(url, files={'photo': photo}, data={'chat_id': chat_id, 'caption': '📸 运行截图'}, timeout=15)

async def run():
    async with async_playwright() as p:
        # 使用 Xray 转出的本地 SOCKS5 代理
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": "socks5://127.0.0.1:1080"}
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        msg = ""
        pic = "debug.png"

        try:
            print("正在通过 VLESS 代理访问...")
            await page.goto("https://dash.icehost.pl/login", timeout=60000)
            await asyncio.sleep(10) # 穿透 Cloudflare 防护层

            # 定位登录框
            email_input = page.locator('input[name="email"]')
            if await email_input.is_visible():
                await email_input.fill(os.environ['ICE_EMAIL'])
                await page.fill('input[name="password"]', os.environ['ICE_PASSWORD'])
                await page.click('button[type="submit"]')
                
                # 等待跳转到后台
                await page.wait_for_url("**/dashboard", timeout=25000)
                
                # 跳转到具体的服务器续期页面
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                await asyncio.sleep(5)
                
                # 寻找续期按钮
                btn = page.get_by_text("增加6小时的有效期")
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(3)
                    await page.screenshot(path=pic)
                    msg = "✅ **续期指令发送成功！**"
                    send_tg_photo(pic)
                else:
                    msg = "⚠️ **按钮未发现**：可能尚未到续期时间（冷却中）。"
                    await page.screenshot(path=pic)
                    send_tg_photo(pic)
            else:
                await page.screenshot(path=pic)
                msg = f"❌ **代理访问失败**：未能加载登录页面。标题：`{await page.title()}`"
                send_tg_photo(pic)

        except Exception as e:
            await page.screenshot(path=pic)
            msg = f"🔥 **脚本异常**: `{str(e)[:100]}`"
            send_tg_photo(pic)
        finally:
            send_tg_msg(msg)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
