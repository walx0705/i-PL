import os
import time
import subprocess
import requests
from seleniumbase import SB

# --- 核心配置（完全保留你的） ---
SERVER_URL = "https://dash.icehost.pl/server/bfe8ebd5"
LOGIN_URL = "https://dash.icehost.pl/login"
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"
HY2_URL = "83.168.94.238:30045"
HY2_AUTH = "9afd1229-b893-40c1-84dd-51e7ce204913"

# --- TG 发送逻辑（完全保留你的） ---
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
    # --- 启动 Hysteria2 客户端（完全保留你的） ---
    config_content = f"server: {HY2_URL}\nauth: {HY2_AUTH}\nsocks5:\n  listen: 127.0.0.1:1080\ntls:\n  sni: www.bing.com\n  insecure: true"
    with open("config.yaml", "w") as f: f.write(config_content)
    proxy_process = subprocess.Popen(["./hysteria", "client", "-c", "config.yaml"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

    # 改用 SeleniumBase UC 模式处理登录检测
    with SB(uc=True, headless=True, proxy="socks5://127.0.0.1:1080") as sb:
        try:
            print("🌐 代理访问中...")
            # 模拟你的 page.goto
            sb.uc_open_with_reconnect(SERVER_URL, reconnect_time=10)
            time.sleep(20)

            # --- 自动登录逻辑（完全保留你的逻辑顺序） ---
            if "login" in sb.get_current_url() or sb.is_element_visible('input[name="username"]'):
                sb.uc_open_with_reconnect(LOGIN_URL, reconnect_time=5)
                sb.type('input[name="username"]', os.environ.get("PTERODACTYL_EMAIL"))
                sb.type('input[name="password"]', os.environ.get("PTERODACTYL_PASSWORD"))
                sb.click('button[type="submit"]')
                time.sleep(10)
                sb.uc_open_with_reconnect(SERVER_URL, reconnect_time=5)
                time.sleep(15)

            # --- 点击按钮逻辑（完全保留你的定位方式） ---
            # 使用 SeleniumBase 对应的 contains 选择器
            btn = f'button:contains("{RENEW_BUTTON_TEXT}")'
            
            if sb.is_element_visible(btn):
                print("🎯 执行点击并识别...")
                sb.click(btn)
                
                final_caption = "❓ 已点击按钮，但未捕捉到明确反馈。"
                # --- 轮询检测弹窗（完全保留你的原始选择器和循环） ---
                for _ in range(10):
                    time.sleep(0.5)
                    # 适配你原来的选择器：.alert-success, .bg-green-500 等
                    if sb.is_element_visible(".alert-success") or \
                       sb.is_element_visible(".bg-green-500") or \
                       sb.is_text_visible("SUKCES") or \
                       sb.is_text_visible("Pomyślnie"):
                        final_caption = "✅ **通过代理续期成功**"
                        break
                    elif sb.is_element_visible(".alert-danger") or \
                         sb.is_element_visible(".bg-red-500") or \
                         sb.is_text_visible("Nie możesz") or \
                         sb.is_text_visible("ERROR"):
                        final_caption = "❌ **未到续期时间**"
                        break
                
                sb.save_screenshot(last_shot)
            else:
                sb.save_screenshot(last_shot)
                final_caption = "🔍 未发现续期按钮。"
        except Exception as e:
            final_caption = f"🚨 运行异常: {str(e)[:30]}"
            try: sb.save_screenshot(last_shot)
            except: pass
        finally:
            # --- 收尾逻辑（完全保留你的） ---
            send_tg_photo(last_shot, final_caption)
            proxy_process.kill()

if __name__ == "__main__":
    run_renew()
