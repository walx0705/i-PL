import os
import time
import requests
from playwright.sync_api import sync_playwright

# --- 配置区 ---
SERVER_URL = "https://dash.icehost.pl/server/bfe8ebd5"
LOGIN_URL = "https://dash.icehost.pl/login"
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"

def send_tg_photo(photo_path, caption):
    """发送图片通知到 Telegram"""
    tg_token = os.environ.get("TG_TOKEN")
    tg_id = os.environ.get("TG_CHAT_ID")
    if not tg_token or not tg_id or not os.path.exists(photo_path):
        return
    url = f"https://api.telegram.org/bot{tg_token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            requests.post(url, data={'chat_id': tg_id, 'caption': caption}, files={'photo': photo}, timeout=30)
    except Exception as e:
        print(f"TG发送失败: {e}")

def run_renew():
    last_shot = "final_status.png"
    final_caption = "⚠️ 脚本运行完成，请检查截图"
    
    with sync_playwright() as p:
        # 深度伪装启动参数
        browser = p.chromium.launch(headless=True, args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled"
        ])
        
        # 模拟真实浏览器环境
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        
        # 1. 注入 Cookie
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            print("🍪 正在注入现有 Cookie...")
            for item in raw_cookies.strip().split(';'):
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    context.add_cookies([{
                        'name': name.strip(), 'value': value.strip(),
                        'domain': 'dash.icehost.pl', 'path': '/', 'secure': True
                    }])

        page = context.new_page()
        page.set_default_timeout(100000)

        try:
            print(f"🚀 访问面板: {SERVER_URL}")
            page.goto(SERVER_URL, wait_until="commit")
            
            # 暴力等待 Cloudflare 5秒盾和页面渲染
            print("⏳ 穿透检测中，等待 30 秒...")
            time.sleep(30) 

            # 2. 自动检测并登录
            if "login" in page.url or page.locator('input[name="username"]').is_visible():
                print("🔑 Cookie 失效，尝试账号密码自动登录...")
                page.goto(LOGIN_URL)
                page.fill('input[name="username"]', os.environ.get("PTERODACTYL_EMAIL"))
                page.fill('input[name="password"]', os.environ.get("PTERODACTYL_PASSWORD"))
                page.click('button[type="submit"]')
                time.sleep(15) # 等待登录跳转
                page.goto(SERVER_URL)
                time.sleep(15)

            # 3. 寻找按钮并执行点击
            btn = page.locator(f'button:has-text("{RENEW_BUTTON_TEXT}")').first
            
            if btn.count() > 0 and btn.is_visible():
                print("🎯 发现按钮！执行强制点击...")
                # 标记点击位置并在截图前稍微等待
                btn.evaluate("el => el.style.border = '10px solid red'")
                btn.click(force=True)
                time.sleep(5)
                page.screenshot(path=last_shot)
                final_caption = "✅ 续期动作已执行！(已完成登录补位)"
            else:
                page.screenshot(path=last_shot)
                if "Connection Blocked" in page.content():
                    final_caption = "❌ Connection Blocked: GitHub IP 被彻底封锁了。"
                elif "Verify you are human" in page.content():
                    final_caption = "🛡️ 未能穿透 Cloudflare 验证码。"
                else:
                    final_caption = "🔍 页面已加载但未发现按钮，请参考截图。"

        except Exception as e:
            final_caption = f"🚨 崩溃: {str(e)[:50]}"
            page.screenshot(path=last_shot)
        finally:
            send_tg_photo(last_shot, final_caption)
            browser.close()

if __name__ == "__main__":
    run_renew()
