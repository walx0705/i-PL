import os
import asyncio
import sys
import requests
from playwright.async_api import async_playwright

# --- 配置 ---
BASE_URL = "https://icehost.pl" 
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"

def send_tg_msg(message):
    """发送通知到 Telegram 并打印详细日志"""
    tg_token = os.environ.get("TG_TOKEN")
    tg_id = os.environ.get("TG_CHAT_ID")
    
    if not tg_token or not tg_id:
        print("❌ TG 配置缺失，跳过通知")
        return

    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": tg_id, "text": message}, timeout=10)
        print(f"TG 响应: {res.status_code}, {res.text}")
    except Exception as e:
        print(f"TG 发送异常: {e}")

async def run_task():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # 1. 注入 Cookie
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            formatted_cookies = []
            clean_raw = raw_cookies.replace('\n', '').replace('\r', '').strip()
            for item in clean_raw.split(';'):
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    formatted_cookies.append({
                        'name': name.strip(), 'value': value.strip(),
                        'domain': 'icehost.pl', 'path': '/',
                        'secure': True, 'sameSite': 'Lax'
                    })
            await context.add_cookies(formatted_cookies)

        page = await context.new_page() # 确保 page 在 try 之前定义

        try:
            print(f"🚀 正在访问: {BASE_URL}")
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)

            # 2. 检查是否需要登录
            if await page.query_selector('input[name="username"]'):
                print("⚠️ Cookie 无效，尝试账号密码登录...")
                email = os.environ.get("PTERODACTYL_EMAIL")
                pw = os.environ.get("PTERODACTYL_PASSWORD")
                if email and pw:
                    await page.fill('input[name="username"]', email)
                    await page.fill('input[name="password"]', pw)
                    await page.click('button[type="submit"]')
                    await page.wait_for_load_state("networkidle")

            # 3. 寻找并点击续期按钮
            print(f"🔍 寻找按钮: {RENEW_BUTTON_TEXT}")
            selector = f'text="{RENEW_BUTTON_TEXT}"'
            btn = await page.wait_for_selector(selector, timeout=20000)
            
            if btn:
                await btn.click()
                msg = "✅ IceHost 续期成功！已增加 6 小时。"
                print(msg)
                send_tg_msg(msg)
                await asyncio.sleep(5)
                await page.screenshot(path="success.png")
            else:
                print("❌ 未找到按钮")
                await page.screenshot(path="not_found.png")

        except Exception as e:
            err_msg = f"🚨 运行错误: {str(e)}"
            print(err_msg)
            send_tg_msg(err_msg)
            await page.screenshot(path="error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_task())
