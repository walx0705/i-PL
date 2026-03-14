import os
import asyncio
import sys
import requests  # 新增
from playwright.async_api import async_playwright

# --- 配置参数 ---
BASE_URL = "https://icehost.pl" 
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"

# Telegram 配置
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_tg_msg(message):
    """简单的 TG 发送函数"""
    if TG_TOKEN and TG_CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": message}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"TG 通知发送失败: {e}")

async def run_task():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        # ... (注入 Cookie 的逻辑保持不变) ...

        try:
            # ... (登录和跳转逻辑保持不变) ...

            # 定位并点击续期按钮
            selector = f'text="{RENEW_BUTTON_TEXT}"'
            btn = await page.wait_for_selector(selector, timeout=30000)
            
            if btn:
                await btn.click()
                msg = "✅ IceHost 续期成功！已增加 6 小时。"
                print(msg)
                send_tg_msg(msg) # 发送成功通知
                await asyncio.sleep(5)
            else:
                send_tg_msg("⚠️ 未能找到续期按钮，请检查面板。")
                
        except Exception as e:
            send_tg_msg(f"🚨 IceHost 续期脚本运行报错: {e}")
            raise e
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_task())
