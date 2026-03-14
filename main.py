import os
import time
import sys
import requests
from playwright.sync_api import sync_playwright

# --- 配置 ---
SERVER_URL = "https://dash.icehost.pl/server/bfe8ebd5"
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"

def send_tg_photo(photo_path, caption):
    """发送图片通知的核心函数"""
    tg_token = os.environ.get("TG_TOKEN")
    tg_id = os.environ.get("TG_CHAT_ID")
    if not tg_token or not tg_id:
        print("❌ TG 配置缺失")
        return
    if not os.path.exists(photo_path):
        print(f"❌ 找不到图片文件: {photo_path}")
        return

    url = f"https://api.telegram.org/bot{tg_token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            res = requests.post(
                url, 
                data={'chat_id': tg_id, 'caption': caption}, 
                files={'photo': photo}, 
                timeout=30
            )
            print(f"TG 响应状态: {res.status_code}, 内容: {res.text}")
    except Exception as e:
        print(f"⚠️ TG 发送过程崩溃: {e}")

def run_renew():
    # 初始化一个全局变量存储最后的截图说明
    final_caption = "⚠️ 脚本启动后发生未知错误"
    last_shot = "final_state.png"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        # 设置全局宽容超时
        page.set_default_timeout(80000)

        # 注入 Cookie
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            for item in raw_cookies.strip().split(';'):
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    context.add_cookies([{'name': name.strip(), 'value': value.strip(), 'domain': 'dash.icehost.pl', 'path': '/', 'secure': True}])

        try:
            print(f"🚀 尝试访问页面: {SERVER_URL}")
            # wait_until="commit" 只要服务器有响应就继续，不再死等所有资源加载
            try:
                page.goto(SERVER_URL, wait_until="commit", timeout=60000)
            except Exception as e:
                print(f"⏳ 页面访问超时，但我们将继续尝试寻找按钮。错误: {e}")

            # 停留一会儿等待 JS 渲染按钮
            time.sleep(15)

            # 寻找按钮
            btn = page.locator(f'button:has-text("{RENEW_BUTTON_TEXT}")').first
            
            if btn.count() > 0 and btn.is_visible():
                print("🎯 发现按钮，尝试点击...")
                # 标记一下我们要点的地方
                btn.evaluate("el => el.style.border = '10px solid red'") 
                btn.click(force=True)
                time.sleep(5)
                final_caption = "⚡ 执行了点击动作！请看红框位置。 (注意：若未到时间则点击无效)"
            else:
                print("🔍 没看到按钮，可能是页面没加载出来或 Cookie 失效。")
                final_caption = "❌ 未能定位到续期按钮，请检查截图。"

            page.screenshot(path=last_shot)

        except Exception as e:
            final_caption = f"🚨 脚本运行崩溃: {str(e)[:100]}"
            # 即使崩溃也尝试截一张当下的图
            try:
                page.screenshot(path=last_shot)
            except:
                pass
        finally:
            # --- 无论结果如何，最后一步必然是发 TG 消息 ---
            print("📤 正在推送最后的现场截图到 Telegram...")
            send_tg_photo(last_shot, final_caption)
            browser.close()

if __name__ == "__main__":
    run_renew()
