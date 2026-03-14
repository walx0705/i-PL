import os
import time
import subprocess
import requests
from playwright.sync_api import sync_playwright

# --- 配置区 ---
SERVER_URL = "https://dash.icehost.pl/server/bfe8ebd5"
LOGIN_URL = "https://dash.icehost.pl/login"
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"
# 你的 Hysteria2 节点
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
    last_shot = "proxy_status.png"
    # 启动 Hysteria2 客户端 (简易配置)
    config_content = f"""
server: {HY2_URL}
auth: {HY2_AUTH}
socks5:
  listen: 127.0.0.1:1080
tls:
  sni: www.bing.com
  insecure: true
fastOpen: true
"""
    with open("config.yaml", "w") as f: f.write(config_content)
    
    # 假设已经在 main.yml 下载了 hysteria 二进制文件
    proxy_process = subprocess.Popen(["./hysteria", "client", "-c", "config.yaml"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5) # 等待代理启动

    with sync_playwright() as p:
        # 使用本地 Socks5 代理启动浏览器
        browser = p.chromium.launch(headless=True, proxy={"server": "socks5://127.0.0.1:1080"})
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # 注入 Cookie
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            for item in raw_cookies.strip().split(';'):
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    context.add_cookies([{'name': name.strip(), 'value': value.strip(), 'domain': 'dash.icehost.pl', 'path': '/', 'secure': True}])

        page = context.new_page()
        try:
            print("🌐 正在通过波兰节点访问面板...")
            page.goto(SERVER_URL, wait_until="commit")
            time.sleep(25)

            if "login" in page.url:
                print("🔑 代理环境下 Cookie 失效，执行自动登录...")
                page.goto(LOGIN_URL)
                page.fill('input[name="username"]', os.environ.get("PTERODACTYL_EMAIL"))
                page.fill('input[name="password"]', os.environ.get("PTERODACTYL_PASSWORD"))
                page.click('button[type="submit"]')
                time.sleep(15)
                page.goto(SERVER_URL)
                time.sleep(15)

            btn = page.locator(f'button:has-text("{RENEW_BUTTON_TEXT}")').first
            if btn.count() > 0:
                btn.evaluate("el => el.style.border = '10px solid red'")
                btn.click(force=True)
                time.sleep(5)
                page.screenshot(path=last_shot)
                msg = "✅ [代理模式] 续期执行成功！"
            else:
                page.screenshot(path=last_shot)
                msg = "🔍 [代理模式] 未发现按钮，请查图。"
        except Exception as e:
            msg = f"🚨 代理连接异常: {str(e)[:30]}"
            page.screenshot(path=last_shot)
        finally:
            send_tg_photo(last_shot, msg)
            browser.close()
            proxy_process.kill()

if __name__ == "__main__":
    run_renew()
