import os
import asyncio
import requests
from playwright.async_api import async_playwright

# 发送 TG 文字消息
def send_tg_msg(message):
    token = os.environ.get('TG_BOT_TOKEN')
    chat_id = os.environ.get('TG_CHAT_ID')
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": f"🤖 **IceHost 续期助手**\n\n{message}", "parse_mode": "Markdown"}
        requests.post(url, data=data, timeout=10)

# 发送 TG 图片消息
def send_tg_photo(photo_path):
    token = os.environ.get('TG_BOT_TOKEN')
    chat_id = os.environ.get('TG_CHAT_ID')
    if token and chat_id and os.path.exists(photo_path):
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {'chat_id': chat_id, 'caption': '📸 失败现场截图'}
            requests.post(url, files=files, data=data, timeout=15)

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        msg = ""
        screenshot_path = "error.png"

        try:
            print("正在访问...")
            # 访问页面
            await page.goto("https://dash.icehost.pl/login", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(10) # 给 5 秒盾留出时间

            # 检查登录框
            email_input = page.locator('input[name="email"]')
            if await email_input.is_visible():
                # 如果能看到登录框，说明没被 Block
                await email_input.fill(os.environ['ICE_EMAIL'])
                await page.fill('input[name="password"]', os.environ['ICE_PASSWORD'])
                await page.click('button[type="submit"]')
                await page.wait_for_url("**/dashboard", timeout=20000)
                
                # 续期逻辑
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                renew_btn = page.get_by_text("增加6小时的有效期")
                if await renew_btn.is_visible():
                    await renew_btn.click()
                    msg = "✅ **续期指令发送成功**"
                else:
                    msg = "⚠️ **未发现按钮** (可能在冷却中)"
            else:
                # 如果没看到登录框，截图并报错
                await page.screenshot(path=screenshot_path)
                msg = f"❌ **拦截失败**\n页面标题: `{await page.title()}`\n截图已发送至 TG。"
                send_tg_photo(screenshot_path)

        except Exception as e:
            await page.screenshot(path=screenshot_path)
            msg = f"🔥 **异常**: `{str(e)[:50]}...`"
            send_tg_photo(screenshot_path)
        finally:
            send_tg_msg(msg)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
