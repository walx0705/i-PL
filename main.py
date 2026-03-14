import os
import asyncio
import requests
import random
from playwright.async_api import async_playwright

# --- 基础配置 ---
ICE_EMAIL = os.environ.get('ICE_EMAIL')
ICE_PASSWORD = os.environ.get('ICE_PASSWORD')
TG_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')
PROXY_SERVER = "socks5://127.0.0.1:1080"

def send_tg_msg(message):
    if TG_TOKEN and TG_CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": f"🤖 **IceHost 物理按键模拟版**\n\n{message}", "parse_mode": "Markdown"}
        try: requests.post(url, data=data, timeout=10)
        except: pass

async def run():
    async with async_playwright() as p:
        # 1. 深度指纹混淆启动
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY_SERVER})
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # 抹除所有机器人特征
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        debug_pic = "keyboard_attempt.png"

        try:
            print("正在尝试穿透 Cloudflare...")
            await page.goto("https://dash.icehost.pl/login", wait_until="networkidle", timeout=90000)
            
            # 2. 暴力等待 30 秒，确保 Cloudflare 盾牌跑完
            await asyncio.sleep(30)
            
            # 3. 键盘模拟大法：不管能不能看到框，直接一通操作
            print("执行物理键盘模拟输入...")
            # 连点 5 次 Tab 确保焦点进入表单（根据 IceHost 页面结构）
            for _ in range(5):
                await page.keyboard.press("Tab")
                await asyncio.sleep(0.5)
            
            # 输入邮箱
            await page.keyboard.type(ICE_EMAIL, delay=100)
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.5)
            
            # 输入密码
            await page.keyboard.type(ICE_PASSWORD, delay=100)
            await page.keyboard.press("Enter")
            
            print("已通过键盘提交，等待跳转...")
            
            # 4. 验证是否成功进入 Dashboard
            try:
                await page.wait_for_url("**/dashboard", timeout=40000)
                print("🎉 物理模拟成功！已登录。")
                
                # 续期流程
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                await asyncio.sleep(10)
                await page.get_by_text("6h").click()
                send_tg_msg("🚀 **物理按键模拟填表成功，续期已完成！**")
            except:
                await page.screenshot(path=debug_pic)
                send_tg_msg("❌ 键盘填表提交后未能跳转。Cloudflare 可能直接拒绝了非人工点击的提交。")

        except Exception as e:
            await page.screenshot(path=debug_pic)
            send_tg_msg(f"🔥 物理模拟报错: `{str(e)[:100]}`")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
