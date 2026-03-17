import os
import time
import subprocess
import requests
from playwright.sync_api import sync_playwright
from seleniumbase import SB  # 新增：用于解决登录验证

# --- 核心配置（保持原样） ---
SERVER_URL = "https://dash.icehost.pl/server/bfe8ebd5"
LOGIN_URL = "https://dash.icehost.pl/login"
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"
HY2_URL = "83.168.94.238:30045"
HY2_AUTH = "9afd1229-b893-40c1-84dd-51e7ce204913"

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
    # 启动 Hysteria2 客户端
    config_content = f"server: {HY2_URL}\nauth: {HY2_AUTH}\nsocks5:\n  listen: 127.0.0.1:1080\ntls:\n  sni: www.bing.com\n  insecure: true"
    with open("config.yaml", "w") as f: f.write(config_content)
    proxy_process = subprocess.Popen(["./hysteria", "client", "-c", "config.yaml"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

    # --- 第一步：使用 SeleniumBase 解决登录验证并获取 Cookies ---
    cookies = []
    print("🔑 正在通过 SeleniumBase 处理登录验证...")
    with SB(uc=True, headless=True, proxy="socks5://127.0.0.1:1080") as sb:
        sb.uc_open_with_reconnect(LOGIN_URL, reconnect_time=10)
        if sb.is_element_visible('input[name="username"]'):
            sb.type('input[name="username"]', os.environ.get("PTERODACTYL_EMAIL"))
            sb.type('input[name="password"]', os.environ.get("PTERODACTYL_PASSWORD"))
            sb.click('button[type="submit"]')
            sb.sleep(10)
            cookies = sb.get_cookies() # 拿到登录后的关键信息
            print("✅ 登录成功，已获取会话 Cookies")

    # --- 第二步：将 Cookies 传给你的原始 Playwright 逻辑 ---
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy={"server": "socks5://127.0.0.1:1080"})
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # 注入从 SB 拿到的 Cookies
        if cookies:
            context.add_cookies(cookies)
        
        # 同时也保留你原来的 Cookie 注入逻辑
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            for item in raw_cookies.strip().split(';'):
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    context.add_cookies([{'name': name.strip(), 'value': value.strip(), 'domain': 'dash.icehost.pl', 'path': '/', 'secure': True}])

        page = context.new_page()
        try:
            print("🌐 代理访问中 (Playwright)...")
            page.goto(SERVER_URL, wait_until="commit")
            time.sleep(20)

            # 如果还是没登录成功，执行你原有的 Playwright 登录兜底
            if "login" in page.url or page.locator('input[name="username"]').is_visible():
                page.goto(LOGIN_URL)
                page.fill('input[name="username"]', os.environ.get("PTERODACTYL_EMAIL"))
                page.fill('input[name="password"]', os.environ.get("PTERODACTYL_PASSWORD"))
                page.click('button[type="submit"]')
                time.sleep(10)
                page.goto(SERVER_URL)
                time.sleep(15)

            # --- 下面完全是你原来的点击和通知逻辑，一行没动 ---
            btn = page.locator(f'button:has-text("{RENEW_BUTTON_TEXT}")').first
            if btn.count() > 0:
                print("🎯 执行点击并识别...")
                btn.click(force=True)
                
                final_caption = "❓ 已点击按钮，但未捕捉到明确反馈。"
                for _ in range(10): 
                    time.sleep(0.5)
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
