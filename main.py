import os
import time
import subprocess
import requests
from seleniumbase import SB

# --- 核心配置 ---
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
            requests.post(url, data={'chat_id': tg_id, 'caption': caption}, files={'photo': photo}, timeout=30)
    except: pass

def run_renew():
    last_shot = "final_status.png"
    
    # 1. 启动 Hysteria2 代理 (保持原逻辑)
    config_content = f"server: {HY2_URL}\nauth: {HY2_AUTH}\nsocks5:\n  listen: 127.0.0.1:1080\ntls:\n  sni: www.bing.com\n  insecure: true"
    with open("config.yaml", "w") as f: f.write(config_content)
    proxy_process = subprocess.Popen(["./hysteria", "client", "-c", "config.yaml"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

    # 2. 使用 SeleniumBase UC 模式
    # headless=True 在 Linux 服务器运行，proxy 设置为本地 socks5
    with SB(uc=True, headless=True, proxy="socks5://127.0.0.1:1080") as sb:
        try:
            print("🌐 正在通过代理访问服务器页面...")
            # 使用关键的 uc_open_with_reconnect 绕过初始检测
            sb.uc_open_with_reconnect(SERVER_URL, reconnect_time=10.0)
            sb.sleep(10)

            # 3. 自动登录逻辑
            if "login" in sb.get_current_url() or sb.is_element_visible('input[name="username"]'):
                print("🔑 检测到登录墙，正在登录...")
                sb.type('input[name="username"]', os.environ.get("PTERODACTYL_EMAIL"))
                sb.type('input[name="password"]', os.environ.get("PTERODACTYL_PASSWORD"))
                sb.click('button[type="submit"]')
                sb.sleep(10)
                sb.uc_open_with_reconnect(SERVER_URL, reconnect_time=5.0)
                sb.sleep(5)

            # 4. 核心：寻找并点击续期按钮
            # 使用包含文本的选择器
            btn_selector = f'button:contains("{RENEW_BUTTON_TEXT}")'
            
            if sb.is_element_visible(btn_selector):
                print("🎯 发现续期按钮，尝试点击并处理验证...")
                
                # 触发点击
                sb.click(btn_selector)
                sb.sleep(3)
                
                # --- 加入 SeleniumBase 的过验证杀手锏 ---
                # 自动检测并点击 Cloudflare Turnstile 或类似的验证复选框
                try:
                    sb.uc_gui_click_captcha() 
                    print("✅ 尝试执行了 GUI 智能点击验证")
                    sb.sleep(5)
                except:
                    pass

                # 5. 检查执行结果
                final_caption = "❓ 已操作，但未获取到反馈结果。"
                # 轮询检测页面上的提示信息
                for _ in range(20):
                    if sb.is_text_visible("SUKCES") or sb.is_text_visible("Pomyślnie"):
                        final_caption = "✅ **续期成功！**"
                        break
                    elif sb.is_text_visible("Nie możesz") or sb.is_text_visible("ERROR"):
                        final_caption = "❌ **未到续期时间或操作失败**"
                        break
                    sb.sleep(0.5)
                
                sb.save_screenshot(last_shot)
            else:
                sb.save_screenshot(last_shot)
                final_caption = "🔍 未发现续期按钮，请检查页面状态。"

        except Exception as e:
            final_caption = f"🚨 运行异常: {str(e)[:50]}"
            sb.save_screenshot(last_shot)
        finally:
            send_tg_photo(last_shot, final_caption)
            proxy_process.kill()

if __name__ == "__main__":
    run_renew()
