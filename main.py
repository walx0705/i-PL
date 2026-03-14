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
        except Exception as e:
            print(f"TG通知发送失败: {e}")

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        msg = ""
        try:
            print("正在登录...")
            await page.goto("https://dash.icehost.pl/login")
            await page.fill('input[name="email"]', os.environ['ICE_EMAIL'])
            await page.fill('input[name="password"]', os.environ['ICE_PASSWORD'])
            await page.click('button[type="submit"]')
            await page.wait_for_url("**/dashboard", timeout=20000)
            
            print("访问服务器页面...")
            await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
            await page.wait_for_load_state("networkidle")

            renew_btn = page.get_by_text("增加6小时的有效期")
            if await renew_btn.is_visible():
                await renew_btn.click()
                await asyncio.sleep(5)
                error_box = page.locator('.alert-danger, .error-message')
                if await error_box.is_visible():
                    msg = f"❌ **续期失败**\n原因: `{await error_box.inner_text()}`"
                else:
                    msg = "✅ **续期指令发送成功**"
            else:
                msg = "⚠️ **未发现按钮** (可能在冷却中)"
        except Exception as e:
            msg = f"🔥 **运行异常**: `{str(e)}`"
        finally:
            send_tg_msg(msg)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
