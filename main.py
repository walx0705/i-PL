import os
import time
import subprocess
import requests
import json
from playwright.sync_api import sync_playwright
from seleniumbase import SB

# --- 核心配置 ---
SERVER_URL = "https://dash.icehost.pl/server/92d3015f"
LOGIN_URL = "https://dash.icehost.pl/login"
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"
HY2_URL = "83.168.94.238:30086"
HY2_AUTH = "515490ac-c0eb-4a4e-91d1-a5454b7e5fd6"
COOKIE_FILE = "session_cookies.json"

def send_tg_photo(photo_path, caption):
    tg_token = os.environ.get("TG_TOKEN")
    tg_id = os.environ.get("TG_CHAT_ID")
    if not tg_token or not tg_id or not os.path.exists(photo_path): return
    url = f"https://api.telegram.org/bot{tg_token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            requests.post(url, data={'chat_id': tg_id, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': photo}, timeout=30)
    except: pass

def run_renew():
    last_shot = "final_status.png"
    # 1. 启动 Hysteria2 代理
    config_content = (
        f"server: {HY2_URL}\n"
        f"auth: {HY2_AUTH}\n"
        "socks5:\n"
        "  listen: 127.0.0.1:1080\n"
        "tls:\n"
        "  sni: www.bing.com\n"
        "  insecure: true\n"
        "  alpn:\n"
        "    - h3"
    )
    with open("config.yaml", "w") as f: f.write(config_content)
    proxy_process = subprocess.Popen(["./hysteria", "client", "-c", "config.yaml"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

    final_caption = "🔍 未知状态"
    playwright_cookies = []

    # 优先加载本地存储的 Cookie
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, 'r') as f:
            playwright_cookies = json.load(f)
            print("🍪 已加载本地缓存的 Cookie")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy={"server": "socks5://127.0.0.1:1080"})
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        if playwright_cookies:
            context.add_cookies(playwright_cookies)

        page = context.new_page()
        try:
            print("🌐 尝试使用 Cookie 访问续期界面...")
            page.goto(SERVER_URL, wait_until="commit", timeout=60000)
            time.sleep(10)

            # --- 2. 检查 Cookie 是否失效 ---
            if "login" in page.url or page.locator('input[name="username"]').is_visible():
                print("⚠️ Cookie 已失效，切换 SeleniumBase 进行账号登录...")
                browser.close() # 关闭当前 Playwright 实例

                # 调用 SeleniumBase 重新登录
                with SB(uc=True, headless=True, proxy="socks5://127.0.0.1:1080") as sb:
                    sb.uc_open_with_reconnect(LOGIN_URL, reconnect_time=10)
                    sb.type('input[name="username"]', os.environ.get("PTERODACTYL_EMAIL"))
                    sb.type('input[name="password"]', os.environ.get("PTERODACTYL_PASSWORD"))
                    sb.click('button[type="submit"]')
                    sb.sleep(10)
                    
                    # 获取新 Cookie 并保存
                    new_cookies = sb.get_cookies()
                    playwright_cookies = []
                    for c in new_cookies:
                        playwright_cookies.append({
                            'name': c['name'], 'value': c['value'],
                            'domain': c.get('domain', 'dash.icehost.pl'),
                            'path': c.get('path', '/'), 'secure': c.get('secure', True)
                        })
                    with open(COOKIE_FILE, 'w') as f:
                        json.dump(playwright_cookies, f)
                    print("💾 新 Cookie 已自动保存")

                # 重新打开 Playwright 并注入新 Cookie
                browser = p.chromium.launch(headless=True, proxy={"server": "socks5://127.0.0.1:1080"})
                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                context.add_cookies(playwright_cookies)
                page = context.new_page()
                page.goto(SERVER_URL, wait_until="commit")
                time.sleep(15)

            # --- 3. 续期点击逻辑（保持原始 Playwright 逻辑） ---
            btn = page.locator(f'button:has-text("{RENEW_BUTTON_TEXT}")').first
            if btn.count() > 0:
                print("🎯 执行点击...")
                btn.click(force=True)
                
                final_caption = "❓ 已点击按钮，但未捕捉到反馈。"
                for _ in range(10): 
                    time.sleep(1)
                    success = page.locator(".alert-success, .bg-green-500, :text('SUKCES'), :text('Pomyślnie')").first
                    error = page.locator(".alert-danger, .bg-red-500, :text('Nie możesz'), :text('ERROR')").first
                    
                    if success.count() > 0 and success.is_visible():
                        final_caption = "✅ **通过代理续期成功**"
                        break
                    elif error.count() > 0 and error.is_visible():
                        final_caption = "❌ **未到续期时间**"
                        break
                page.screenshot(path=last_shot)
            else:
                page.screenshot(path=last_shot)
                final_caption = "🔍 未发现续期按钮。"

        except Exception as e:
            final_caption = f"🚨 运行异常: {str(e)[:30]}"
            page.screenshot(path=last_shot)
        finally:
            send_tg_photo(last_shot, final_caption)
            browser.close()
            proxy_process.kill()

if __name__ == "__main__":
    run_renew()
