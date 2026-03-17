import os
import time
import subprocess
import requests
from seleniumbase import SB

# --- 核心配置 ---
SERVER_URL = "https://dash.icehost.pl/server/bfe8ebd5"
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
    except Exception as e:
        print(f"TG发送失败: {e}")

def run_renew():
    last_shot = "final_status.png"
    
    # 1. 启动 Hysteria2 代理
    config_content = f"server: {HY2_URL}\nauth: {HY2_AUTH}\nsocks5:\n  listen: 127.0.0.1:1080\ntls:\n  sni: www.bing.com\n  insecure: true"
    with open("config.yaml", "w") as f: f.write(config_content)
    proxy_process = subprocess.Popen(["./hysteria", "client", "-c", "config.yaml"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

    # 2. 使用 SeleniumBase UC 模式运行
    with SB(uc=True, headless=True, proxy="socks5://127.0.0.1:1080") as sb:
        try:
            print("🌐 正在连接 IceHost 面板...")
            sb.uc_open_with_reconnect(SERVER_URL, reconnect_time=10.0)
            sb.sleep(10)

            # 3. 自动登录逻辑
            if "login" in sb.get_current_url() or sb.is_element_visible('input[name="username"]'):
                print("🔑 正在执行自动登录...")
                sb.type('input[name="username"]', os.environ.get("PTERODACTYL_EMAIL"))
                sb.type('input[name="password"]', os.environ.get("PTERODACTYL_PASSWORD"))
                sb.click('button[type="submit"]')
                sb.sleep(15)
                sb.uc_open_with_reconnect(SERVER_URL, reconnect_time=5.0)

            # 4. 查找并处理续期按钮
            btn_selector = f'button:contains("{RENEW_BUTTON_TEXT}")'
            if sb.is_element_visible(btn_selector):
                print("🎯 发现续期按钮，正在点击...")
                sb.click(btn_selector)
                sb.sleep(3)
                
                # 核心：调用 SeleniumBase 的智能验证码点击功能
                print("🧩 尝试绕过人机验证...")
                try:
                    sb.uc_gui_click_captcha()
                    sb.sleep(8)
                except:
                    pass

                # 5. 结果轮询判定
                final_caption = "❓ 已操作，但未获取到反馈结果。"
                for _ in range(15):
                    # 检查页面上的波兰语成功标志
                    if sb.is_text_visible("SUKCES") or sb.is_text_visible("Pomyślnie"):
                        final_caption = "✅ **续期操作成功！**"
                        break
                    elif sb.is_text_visible("Nie możesz") or sb.is_text_visible("ERROR"):
                        final_caption = "❌ **未到续期时间或系统报错。**"
                        break
                    sb.sleep(1)
                
                sb.save_screenshot(last_shot)
            else:
                sb.save_screenshot(last_shot)
                final_caption = "🔍 页面未发现续期按钮，请检查账户或代理状态。"

        except Exception as e:
            final_caption = f"🚨 运行异常: {str(e)[:50]}"
            try: sb.save_screenshot(last_shot)
            except: pass
        finally:
            send_tg_photo(last_shot, final_caption)
            proxy_process.kill()

if __name__ == "__main__":
    run_renew()
