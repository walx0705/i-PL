import os
import time
import sys
import requests
from playwright.sync_api import sync_playwright

# --- 配置 ---
SERVER_URL = "https://dash.icehost.pl/server/bfe8ebd5"
LOGIN_URL = "https://dash.icehost.pl/login"
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"

def send_tg_photo(photo_path, caption):
    tg_token = os.environ.get("TG_TOKEN")
    tg_id = os.environ.get("TG_CHAT_ID")
    if not tg_token or not tg_id or not os.path.exists(photo_path): return
    url = f"https://api.telegram.org/bot{tg_token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            requests.post(url, data={'chat_id': tg_id, 'caption': caption}, files={'photo': photo}, timeout=30)
    except: pass

def run_renew():
    last_shot = "current_status.png"
    final_caption = "⚠️ 运行结束"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # 1. 优先注入现有 Cookie
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            for item in raw_cookies.strip().split(';'):
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    context.add_cookies([{'name': name.strip(), 'value': value.strip(), 'domain': 'dash.icehost.pl', 'path': '/', 'secure': True}])

        page = context.new_page()
        
        try:
            print("🚀 尝试进入面板...")
            page.goto(SERVER_URL, wait_until="commit")
            time.sleep(20) # 等待 CF 和渲染

            # 2. 【核心逻辑】检测是否需要自动登录更新 Cookie
            if "login" in page.url or page.locator('input[name="username"]').is_visible():
                print("🔑 Cookie 已失效，正在尝试账号密码自动登录...")
                page.goto(LOGIN_URL)
                page.fill('input[name="username"]', os.environ.get("PTERODACTYL_EMAIL"))
                page.fill('input[name="password"]', os.environ.get("PTERODACTYL_PASSWORD"))
                page.click('button[type="submit"]')
                time.sleep(10)
                # 登录后重新跳转回服务器页面
                page.goto(SERVER_URL)
                time.sleep(15)

            # 3. 寻找并点击续期按钮
            btn = page.locator(f'button:has-text("{RENEW_BUTTON_TEXT}")').first
            if btn.count() > 0 and btn.is_visible():
                btn.evaluate("el => el.style.border = '10px solid red'")
                btn.click(force=True)
                time.sleep(5)
                page.screenshot(path=last_shot)
                final_caption = "✅ 续期动作已执行！(已自动处理登录态)"
            else:
                page.screenshot(path=last_shot)
                final_caption = "❌ 依然没看到按钮，请检查截图。"

        except Exception as e:
            final_caption = f"🚨 异常: {str(e)[:50]}"
            page.screenshot(path=last_shot)
        finally:
            send_tg_photo(last_shot, final_caption)
            browser.close()

if __name__ == "__main__":
    run_renew()
