import os
import time
import sys
import requests
from playwright.sync_api import sync_playwright

# --- 核心配置 ---
SERVER_URL = "https://dash.icehost.pl/server/bfe8ebd5"
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"

def send_tg_photo(photo_path, caption):
    tg_token = os.environ.get("TG_TOKEN")
    tg_id = os.environ.get("TG_CHAT_ID")
    if not tg_token or not tg_id or not os.path.exists(photo_path): return
    url = f"https://api.telegram.org/bot{tg_token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            requests.post(url, data={'chat_id': tg_id, 'caption': caption}, files={'photo': photo}, timeout=20)
    except Exception as e: print(f"TG通知失败: {e}")

def run_renew():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={'width': 1280, 'height': 800})

        # 注入 Cookie
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            formatted_cookies = []
            for item in raw_cookies.strip().split(';'):
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    formatted_cookies.append({'name': name.strip(), 'value': value.strip(), 'domain': 'dash.icehost.pl', 'path': '/', 'secure': True, 'sameSite': 'Lax'})
            context.add_cookies(formatted_cookies)

        page = context.new_page()
        
        try:
            print(f"🚀 访问面板: {SERVER_URL}")
            page.goto(SERVER_URL, wait_until="networkidle", timeout=60000)
            time.sleep(15) 

            # 1. 暴力定位按钮（不考虑任何前置逻辑）
            # 优先找蓝色按钮
            btn = page.locator(f'button:has-text("{RENEW_BUTTON_TEXT}")').first
            
            if btn.count() == 0:
                # 备选：通过 CSS 类名寻找
                btn = page.locator('button.btn-primary').filter(has_text="DODAJ").first

            if btn.is_visible():
                print("🎯 发现按钮，尝试强制点击...")
                # 即使被遮挡也强制点击
                btn.click(force=True)
                time.sleep(5)
                
                # 再次截图看是否有弹窗或变化
                page.screenshot(path="after_click.png")
                send_tg_photo("after_click.png", "⚡ 执行了强制点击！请手动刷新手机面板确认时间。")
                return True
            else:
                print("❌ 页面未发现按钮")
                page.screenshot(path="not_found.png")
                send_tg_photo("not_found.png", "⚠️ 没找到续期按钮。服务器可能已彻底关闭，请尝试手动在网页点一下开机。")
                return False

        except Exception as e:
            print(f"🚨 异常: {e}")
            page.screenshot(path="error.png")
            send_tg_photo("error.png", f"🚨 脚本报错: {str(e)[:50]}")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    run_renew()
