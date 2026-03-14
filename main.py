import os
import asyncio
import requests
import random
from playwright.async_api import async_playwright

# --- 核心配置 ---
ICE_EMAIL = os.environ.get('ICE_EMAIL')
ICE_PASSWORD = os.environ.get('ICE_PASSWORD')
TG_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')
PROXY_SERVER = "socks5://127.0.0.1:1080"

def send_tg_msg(message):
    if TG_TOKEN and TG_CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": f"🤖 **IceHost 强攻版**\n\n{message}", "parse_mode": "Markdown"}
        try: requests.post(url, data=data, timeout=10)
        except: pass

async def run():
    async with async_playwright() as p:
        # 1. 模拟最真实的浏览器启动
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY_SERVER})
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            viewport={'width': 393, 'height': 852},
            is_mobile=True
        )
        
        # 彻底抹除自动化特征
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        debug_pic = "force_attempt.png"

        try:
            print("正在强行进入页面...")
            await page.goto("https://dash.icehost.pl/login", wait_until="commit", timeout=90000)
            
            # 2. 暴力等待：给 WAF 校验留够 20 秒，管它显示不显示，时间到就开搞
            await asyncio.sleep(20)

            # 3. 盲填模式：直接通过 JS 注入值，不依赖 Playwright 的定位器
            await page.evaluate(f"""
                document.querySelector('input[name="email"]').value = '{ICE_EMAIL}';
                document.querySelector('input[name="password"]').value = '{ICE_PASSWORD}';
                document.querySelector('button[type="submit"]').click();
            """)
            print("已强行注入账号密码并点击登录...")

            # 4. 检查是否成功
            try:
                await page.wait_for_url("**/dashboard", timeout=30000)
                print("🎉 奇迹出现，登录成功！")
                
                # 续期逻辑
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                await asyncio.sleep(10)
                await page.get_by_text("6h").click()
                send_tg_msg("🚀 **强攻成功！服务器已续期。**")
            except:
                await page.screenshot(path=debug_pic)
                from os import path
                if TG_TOKEN and TG_CHAT_ID and path.exists(debug_pic):
                    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
                    with open(debug_pic, 'rb') as f:
                        requests.post(url, files={'photo': f}, data={'chat_id': TG_CHAT_ID, 'caption': "❌ 强攻失败截图"}, timeout=15)
                send_tg_msg("💔 强攻还是没过。这说明 WAF 彻底锁死了 Actions 运行环境。")

        except Exception as e:
            send_tg_msg(f"🔥 报错: `{str(e)[:50]}`")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
