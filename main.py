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
    
    print(f"--- Telegram 通知调试 ---")
    if not tg_token or not tg_id:
        print("❌ 错误: TG_TOKEN 或 TG_CHAT_ID 环境变量为空，请检查 GitHub Secrets 设置。")
        return

    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    payload = {"chat_id": tg_id, "text": message}
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("✅ Telegram 消息发送成功！")
        else:
            print(f"❌ Telegram 发送失败。状态码: {response.status_code}, 响应内容: {response.text}")
            print(f"💡 提示: 请确保你已经私聊过该 Bot 并点击了 /start。")
    except Exception as e:
        print(f"⚠️ 网络请求异常，无法连接到 Telegram API: {e}")

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
            print(f"已注入 {len(formatted_cookies)} 条 Cookie")

        page = await context.new_page()

        try:
            print(f"🚀 正在打开: {BASE_URL}")
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)

            # 2. 备用登录逻辑
            if await page.query_selector('input[name="username"]'):
                print("⚠️ Cookie 无效，尝试账号密码登录...")
                email = os.environ.get("PTERODACTYL_EMAIL")
                pw = os.environ.get("PTERODACTYL_PASSWORD")
                if email and pw:
                    await page.fill('input[name="username"]', email)
                    await page.fill('input[name="password"]', pw)
                    await page.click('button[type="submit"]')
                    await page.wait_for_load_state("networkidle")

            # 3. 寻找并点击
            print(f"🔍 寻找按钮: {RENEW_BUTTON_TEXT}")
            selector = f'text="{RENEW_BUTTON_TEXT}"'
            try:
                btn = await page.wait_for_selector(selector, timeout=20000)
                if btn:
                    await btn.click()
                    success_info = "✅ IceHost 续期动作执行成功！"
                    print(success_info)
                    send_tg_msg(success_info)
                    await asyncio.sleep(5)
                    await page.screenshot(path="success.png")
                else:
                    print("❌ 页面未发现续期按钮。")
                    await page.screenshot(path="not_found.png")
            except Exception:
                print("⚠️ 定位超时，可能已经续期过了。")
                await page.screenshot(path="timeout.png")

        except Exception as e:
            error_info = f"🚨 脚本运行崩溃: {str(e)}"
            print(error_info)
            send_tg_msg(error_info)
            await page.screenshot(path="fatal_error.png")
            sys.exit(1)
        finally:
            await browser.close()
            print("🏁 任务结束")

if __name__ == "__main__":
    asyncio.run(run_task())
