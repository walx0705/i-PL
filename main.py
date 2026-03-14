import os
import asyncio
import sys
import requests
from playwright.async_api import async_playwright

# --- 配置 ---
BASE_URL = "https://icehost.pl" 
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"

def send_tg_msg(message):
    tg_token = os.environ.get("TG_TOKEN")
    tg_id = os.environ.get("TG_CHAT_ID")
    if tg_token and tg_id:
        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": tg_id, "text": message}, timeout=10)
        except Exception as e:
            print(f"TG通知失败: {e}")

async def run_task():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        # 1. 注入 Cookie
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            formatted_cookies = []
            clean_cookies = raw_cookies.replace('\n', '').replace('\r', '')
            for item in clean_cookies.split(';'):
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    formatted_cookies.append({
                        'name': name, 'value': value, 
                        'domain': 'icehost.pl', 'path': '/', 
                        'secure': True, 'sameSite': 'Lax'
                    })
            await context.add_cookies(formatted_cookies)

        # 先定义 page 为 None，防止 NameError
        page = await context.new_page()

        try:
            print(f"🚀 访问: {BASE_URL}")
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)

            # 2. 检查登录
            if await page.query_selector('input[name="username"]'):
                print("尝试账号登录...")
                email = os.environ.get("PTERODACTYL_EMAIL")
                pw = os.environ.get("PTERODACTYL_PASSWORD")
                if email and pw:
                    await page.fill('input[name="username"]', email)
                    await page.fill('input[name="password"]', pw)
                    await page.click('button[type="submit"]')
                    await page.wait_for_load_state("networkidle")

            # 3. 续期点击
            print(f"🔍 寻找按钮: {RENEW_BUTTON_TEXT}")
            selector = f'text="{RENEW_BUTTON_TEXT}"'
            btn = await page.wait_for_selector(selector, timeout=20000)
            
            if btn:
                await btn.click()
                print("✅ 点击成功")
                send_tg_msg("✅ IceHost 续期成功！")
                await asyncio.sleep(5)
                await page.screenshot(path="success.png")
            else:
                print("❌ 未找到按钮")
                await page.screenshot(path="not_found.png")

        except Exception as e:
            print(f"🚨 运行错误: {e}")
            if page:
                await page.screenshot(path="error.png")
            send_tg_msg(f"🚨 IceHost 续期失败: {str(e)}")
            sys.exit(1)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_task())
