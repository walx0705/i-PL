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
# 代理配置
HY2_URL = "83.168.94.238:30086"
HY2_AUTH = "a2d89731-d759-4652-927d-28ed06ab0614"
COOKIE_FILE = "session_cookies.json"

def send_tg_photo(photo_path, caption):
    tg_token = os.environ.get("TG_TOKEN")
    tg_id = os.environ.get("TG_CHAT_ID")
    
    # 1. 如果没有截图，仅发送纯文本消息作为保底
    if not tg_token or not tg_id:
        print("⚠️ 缺少 TG 环境变量，无法发送消息。")
        return

    if not os.path.exists(photo_path):
        print(f"⚠️ 截图不存在，尝试发送纯文本消息。")
        try:
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            requests.post(url, data={'chat_id': tg_id, 'text': f"⚠️ {caption}\n(注：截图生成失败)", 'parse_mode': 'Markdown'}, timeout=10)
        except Exception as e:
            print(f"❌ 纯文本发送异常: {e}")
        return

    # 2. 如果有截图，发图片
    url = f"https://api.telegram.org/bot{tg_token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            resp = requests.post(url, data={'chat_id': tg_id, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': photo}, timeout=30)
            if resp.status_code != 200:
                print(f"❌ TG 发送图片失败: {resp.text}")
    except Exception as e:
        print(f"❌ TG 发送图片异常: {e}")

def run_renew():
    last_shot = "final_status.png"
    final_caption = "🔍 未知状态"
    
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
    with open("config.yaml", "w") as f: 
        f.write(config_content)
    
    try:
        proxy_process = subprocess.Popen(["./hysteria", "client", "-c", "config.yaml"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)
    except Exception as e:
        print(f"🚨 启动代理失败: {e}")
        send_tg_photo("", f"🚨 **代理启动失败**\n错误: {str(e)}")
        return

    playwright_cookies = []

    # 优先加载本地存储的 Cookie
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, 'r') as f:
                playwright_cookies = json.load(f)
                print("🍪 已加载本地缓存的 Cookie")
        except Exception as e:
            print(f"⚠️ 读取 Cookie 失败: {e}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, proxy={"server": "socks5://127.0.0.1:1080"})
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            if playwright_cookies:
                context.add_cookies(playwright_cookies)

            page = context.new_page()
            try:
                print("🌐 尝试使用 Cookie 访问续期界面...")
                page.goto(SERVER_URL, wait_until="commit", timeout=60000)
                time.sleep(5)

                # --- 2. 检查 Cookie 是否失效 ---
                if "login" in page.url or page.locator('input[name="username"]').is_visible():
                    print("⚠️ Cookie 已失效，切换 SeleniumBase 进行账号登录...")
                    browser.close()

                    pterodactyl_email = os.environ.get("PTERODACTYL_EMAIL")
                    pterodactyl_password = os.environ.get("PTERODACTYL_PASSWORD")
                    
                    if not pterodactyl_email or not pterodactyl_password:
                        raise Exception("缺少 PTERODACTYL_EMAIL 或 PTERODACTYL_PASSWORD 环境变量，无法登录！")

                    with SB(uc=True, headless=True, proxy="socks5://127.0.0.1:1080") as sb:
                        sb.uc_open_with_reconnect(LOGIN_URL, reconnect_time=10)
                        sb.type('input[name="username"]', pterodactyl_email)
                        sb.type('input[name="password"]', pterodactyl_password)
                        sb.click('button[type="submit"]')
                        sb.sleep(10)
                        
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
                    time.sleep(10)

                # --- 3. 续期点击逻辑 ---
                print("🔍 正在寻找续期按钮...")
                btn = page.locator(f'button:has-text("{RENEW_BUTTON_TEXT}")').first
                
                if btn.count() > 0:
                    print("🎯 执行点击...")
                    btn.click(force=True)
                    time.sleep(5)
                    page.screenshot(path=last_shot)
                    
                    success = page.locator(".alert-success, .bg-green-500, :text('SUKCES'), :text('Pomyślnie')").first
                    error = page.locator(".alert-danger, .bg-red-500, :text('Nie możesz'), :text('ERROR')").first
                    
                    if success.count() > 0 and success.is_visible():
                        final_caption = "✅ **通过代理续期成功**"
                    elif error.count() > 0 and error.is_visible():
                        final_caption = "❌ **未到续期时间**"
                    else:
                        final_caption = (
                            f"⚠️ **点击成功，但未检测到反馈元素**\n"
                            f"📍 当前URL: `{page.url}`\n"
                            f"📌 页面Title: {page.title()}"
                        )
                        
                else:
                    page.screenshot(path=last_shot)
                    final_caption = (
                        f"❌ **未发现续期按钮**\n"
                        f"搜索文字: `{RENEW_BUTTON_TEXT}`\n"
                        f"📍 当前URL: `{page.url}`"
                    )

            except Exception as e:
                print(f"🚨 运行异常: {e}")
                try: page.screenshot(path=last_shot)
                except: pass
                final_caption = f"🚨 **脚本运行异常**\n错误信息: `{str(e)[:100]}`"
            
            finally:
                # 核心：无论如何都会调用发送
                send_tg_photo(last_shot, final_caption)
                browser.close()

    except Exception as global_e:
        print(f"🚨 全局异常: {global_e}")
        send_tg_photo("", f"🚨 **全局初始化失败**\n错误信息: `{str(global_e)[:100]}`")
    
    finally:
        proxy_process.kill()
        print("🔄 代理已关闭，脚本结束。")

if __name__ == "__main__":
    run_renew()
