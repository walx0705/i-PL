import os
import time
import subprocess
import requests
from playwright.sync_api import sync_playwright

# --- 配置区 ---
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

    with sync_playwright() as p:
        # 通过波兰节点代理，完美避开 Connection Blocked
        browser = p.chromium.launch(headless=True, proxy={"server": "socks5://127.0.0.1:1080"})
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # 注入去空格版 Cookie
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            for item in raw_cookies.strip().split(';'):
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    context.add_cookies([{'name': name.strip(), 'value': value.strip(), 'domain': 'dash.icehost.pl', 'path': '/', 'secure': True}])

        page = context.new_page()
        try:
            print("🌐 正在通过代理访问管理后台...")
            page.goto(SERVER_URL, wait_until="commit")
            time.sleep(20)

            # 自动补位登录：如果 Cookie 失效，脚本会自动输入账号密码
            if "login" in page.url or page.locator('input[name="username"]').is_visible():
                print("🔑 Cookie失效，正在自动登录...")
                page.goto(LOGIN_URL)
                page.fill('input[name="username"]', os.environ.get("PTERODACTYL_EMAIL"))
                page.fill('input[name="password"]', os.environ.get("PTERODACTYL_PASSWORD"))
                page.click('button[type="submit"]')
                time.sleep(10)
                page.goto(SERVER_URL)
                time.sleep(15)

            btn = page.locator(f'button:has-text("{RENEW_BUTTON_TEXT}")').first
            if btn.count() > 0:
                print("🎯 发现按钮，尝试点击...")
                btn.click(force=True)
                time.sleep(8) # 等待上方红/绿提示框弹出

                # --- 智能识别上方红绿弹窗 ---
                # 绿色弹窗通常包含 success 或 bg-green 类；红色包含 danger 或 bg-red 类
                success_box = page.locator(".alert-success, .bg-green-500, .text-green-600").first
                error_box = page.locator(".alert-danger, .bg-red-500, .text-red-600").first

                if success_box.count() > 0 and success_box.is_visible():
                    final_caption = f"✅ **续期成功(绿字)！**\n提示：{success_box.inner_text()}"
                elif error_box.count() > 0 and error_box.is_visible():
                    # 这里对应你说的“没到时间提示红字”
                    final_caption = f"❌ **操作受限(红字)**\n反馈：{error_box.inner_text()}\n(大概率是CD未到，脚本将在3小时后重试)"
                else:
                    final_caption = "❓ 已点击按钮，但页面未显示红绿反馈，请根据截图判断。"
                
                page.screenshot(path=last_shot)
            else:
                page.screenshot(path=last_shot)
                final_caption = "🔍 页面已加载，但未发现续期按钮，请检查是否已封禁或改版。"

        except Exception as e:
            final_caption = f"🚨 脚本异常: {str(e)[:30]}"
            page.screenshot(path=last_shot)
        finally:
            send_tg_photo(last_shot, final_caption)
            browser.close()
            proxy_process.kill()

if __name__ == "__main__":
    run_renew()
