import os
import time
import sys
import requests
from playwright.sync_api import sync_playwright

# --- 核心配置 ---
SERVER_URL = "https://dash.icehost.pl/server/bfe8ebd5"
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"

def send_tg_msg(message):
    """发送纯文字通知"""
    tg_token = os.environ.get("TG_TOKEN")
    tg_id = os.environ.get("TG_CHAT_ID")
    if not tg_token or not tg_id: return
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": tg_id, "text": message}, timeout=10)
    except Exception as e:
        print(f"TG 文字通知失败: {e}")

def send_tg_photo(photo_path, caption):
    """发送图片通知"""
    tg_token = os.environ.get("TG_TOKEN")
    tg_id = os.environ.get("TG_CHAT_ID")
    if not tg_token or not tg_id or not os.path.exists(photo_path):
        return
    url = f"https://api.telegram.org/bot{tg_token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            res = requests.post(url, data={'chat_id': tg_id, 'caption': caption}, files={'photo': photo}, timeout=20)
            print(f"TG 图片发送状态: {res.status_code}")
    except Exception as e:
        print(f"TG 图片通知失败: {e}")

def run_renew():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        # 注入 Cookie
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            formatted_cookies = []
            for item in raw_cookies.strip().split(';'):
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    formatted_cookies.append({
                        'name': name.strip(), 'value': value.strip(),
                        'domain': 'dash.icehost.pl', 'path': '/',
                        'secure': True, 'sameSite': 'Lax'
                    })
            context.add_cookies(formatted_cookies)

        page = context.new_page()
        page.set_default_timeout(90000)

        try:
            print(f"🚀 访问中: {SERVER_URL}")
            page.goto(SERVER_URL, wait_until="domcontentloaded")
            time.sleep(10) 

            btn = page.get_by_text(RENEW_BUTTON_TEXT)
            
            if btn.count() > 0:
                btn.first.click()
                time.sleep(5)
                # 截图并发送成功通知
                shot_path = "success.png"
                page.screenshot(path=shot_path)
                send_tg_photo(shot_path, "✅ IceHost 续期成功！已点击按钮。")
                return True
            else:
                content = page.content()
                if "2026-03" in content: # 这里的年份会随时间变化
                    print("ℹ️ 已处于续期状态")
                    # 如果你想“已经续期”也发截图，取消下面两行的注释
                    # page.screenshot(path="already.png")
                    # send_tg_photo("already.png", "ℹ️ IceHost: 当前无需续期，页面已是最新状态。")
                    return True
                else:
                    shot_path = "not_found.png"
                    page.screenshot(path=shot_path)
                    send_tg_photo(shot_path, "❌ IceHost: 未发现按钮，请检查 Cookie 或页面。")
                    return False

        except Exception as e:
            err_msg = f"🚨 IceHost 脚本异常: {str(e)[:100]}"
            print(err_msg)
            shot_path = "error.png"
            page.screenshot(path=shot_path)
            send_tg_photo(shot_path, err_msg)
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    if not run_renew():
        sys.exit(1)
