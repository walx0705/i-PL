import os
import time
import subprocess
import requests
from seleniumbase import SB

# --- 核心配置 ---
# 目标服务器 URL
SERVER_URL = "https://dash.icehost.pl/server/bfe8ebd5"
# 按钮文字适配：截图显示为 "DODAJ 6 GODZIN WAŻNOŚCI"
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"
# 代理配置
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
    except Exception as e:
        print(f"TG发送失败: {e}")

def run_renew():
    last_shot = "final_status.png"
    
    # 1. 启动 Hysteria2 代理
    config_content = f"server: {HY2_URL}\nauth: {HY2_AUTH}\nsocks5:\n  listen: 127.0.0.1:1080\ntls:\n  sni: www.bing.com\n  insecure: true"
    with open("config.yaml", "w") as f: f.write(config_content)
    proxy_process = subprocess.Popen(["./hysteria", "client", "-c", "config.yaml"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

    # 2. 使用 SeleniumBase UC 模式
    with SB(uc=True, headless=True, proxy="socks5://127.0.0.1:1080") as sb:
        try:
            print("🌐 正在访问 IceHost 面板...")
            sb.uc_open_with_reconnect(SERVER_URL, reconnect_time=10.0)
            sb.sleep(15) # 增加等待时间确保页面完全加载

            # 3. 自动登录
            if "login" in sb.get_current_url() or sb.is_element_visible('input[name="username"]'):
                print("🔑 正在执行自动登录...")
                sb.type('input[name="username"]', os.environ.get("PTERODACTYL_EMAIL"))
                sb.type('input[name="password"]', os.environ.get("PTERODACTYL_PASSWORD"))
                sb.click('button[type="submit"]')
                sb.sleep(15)
                sb.uc_open_with_reconnect(SERVER_URL, reconnect_time=5.0)

            # 4. 寻找续期按钮 - 优化选择器
            # 截图显示按钮在蓝色区域，我们尝试多种定位方式
            selectors = [
                f'button:contains("{RENEW_BUTTON_TEXT}")', # 精确文本匹配
                'button.btn-primary', # 常用按钮类名
                'a.btn-primary', # 有时是伪装成按钮的链接
                'button:contains("DODAJ")' # 模糊匹配关键动词
            ]
            
            target_btn = None
            for sel in selectors:
                if sb.is_element_visible(sel):
                    target_btn = sel
                    break
            
            if target_btn:
                print(f"🎯 发现按钮: {target_btn}，正在执行点击...")
                sb.click(target_btn)
                sb.sleep(3)
                
                # 5. 处理验证码挑战
                # 针对你截图中的“比大小”验证码
                # 这种验证码通常在点击按钮后弹出。脚本尝试点击复选框。
                print("🧩 尝试绕过人机验证挑战...")
                try:
                    sb.uc_gui_click_captcha() # 模拟真实点击
                    sb.sleep(10)
                except:
                    pass

                # 6. 结果判定
                final_caption = "❓ 已操作，但未获取到明确反馈。"
                for _ in range(20):
                    # 检查页面上的波兰语状态词
                    if sb.is_text_visible("SUKCES") or sb.is_text_visible("Pomyślnie"):
                        final_caption = "✅ **IceHost 续期成功！**"
                        break
                    elif sb.is_text_visible("Nie możesz") or sb.is_text_visible("ERROR"):
                        final_caption = "❌ **续期失败：时间未到或被拦截。**"
                        break
                    sb.sleep(0.5)
                
                sb.save_screenshot(last_shot)
            else:
                sb.save_screenshot(last_shot)
                final_caption = "🔍 脚本未能在页面找到续期按钮，请对照截图检查。"

        except Exception as e:
            final_caption = f"🚨 运行异常: {str(e)[:50]}"
            try: sb.save_screenshot(last_shot)
            except: pass
        finally:
            send_tg_photo(last_shot, final_caption)
            proxy_process.kill()

if __name__ == "__main__":
    run_renew()
