import os
import time
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

SERVER_URL = "https://dash.icehost.pl/server/bfe8ebd5"
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
    last_shot = "final_status.png"
    with sync_playwright() as p:
        # 启动浏览器时禁用自动化特征
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 应用隐身脚本
        stealth_sync(page)

        # 注入你刚去空格后的最新 Cookie
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            for item in raw_cookies.strip().split(';'):
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    context.add_cookies([{'name': name.strip(), 'value': value.strip(), 'domain': 'dash.icehost.pl', 'path': '/', 'secure': True}])

        try:
            # 增加访问前的随机延迟，降低被封概率
            print("🚀 正在尝试绕过防火墙...")
            page.goto(SERVER_URL, wait_until="commit", timeout=90000)
            
            # 暴力等待 Cloudflare 5秒盾自动放行
            time.sleep(30) 

            # 截图看一眼是 Blocked 还是已经进入
            page.screenshot(path=last_shot)
            
            if "Connection Blocked" in page.content():
                send_tg_photo(last_shot, "❌ 依然被 IP 封锁。建议停止运行 4 小时后再试。")
                return

            btn = page.locator(f'button:has-text("{RENEW_BUTTON_TEXT}")').first
            if btn.count() > 0:
                btn.click(force=True)
                time.sleep(5)
                send_tg_photo(last_shot, "✅ 破盾成功并点击了按钮！")
            else:
                send_tg_photo(last_shot, "🔍 没看到按钮，看截图是不是卡在验证码了？")
        except Exception as e:
            page.screenshot(path=last_shot)
            send_tg_photo(last_shot, f"🚨 运行崩溃: {str(e)[:50]}")
        finally:
            browser.close()

if __name__ == "__main__":
    run_renew()
