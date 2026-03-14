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
        data = {"chat_id": TG_CHAT_ID, "text": f"🤖 **IceHost 续期(验证码挑战版)**\n\n{message}", "parse_mode": "Markdown"}
        try: requests.post(url, data=data, timeout=10)
        except: pass

async def run():
    async with async_playwright() as p:
        # 启动浏览器并混淆指纹
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY_SERVER})
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # 注入 Stealth 脚本绕过 reCAPTCHA 检测
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        debug_pic = "captcha_challenge.png"

        try:
            print("正在穿透 Cloudflare/reCAPTCHA...")
            await page.goto("https://dash.icehost.pl/login", wait_until="networkidle", timeout=90000)
            
            # 关键：给验证码充分的加载和自动验证时间
            await asyncio.sleep(25) 
            
            # 动态检测输入框
            email_field = page.locator('input[name="email"]')
            if await email_field.is_hidden():
                print("检测到验证码遮挡，尝试强制等待...")
                await asyncio.sleep(15)

            if await email_field.is_visible():
                print("✅ 绕过成功，填表登录...")
                await email_field.fill(ICE_EMAIL)
                await page.fill('input[name="password"]', ICE_PASSWORD)
                
                # 点击登录按钮
                await page.click('button[type="submit"]')
                await page.wait_for_url("**/dashboard", timeout=45000)
                
                # 进入服务器页并续期
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                await asyncio.sleep(8)
                
                # 模糊匹配按钮，防止波兰语/英语差异
                renew_btn = page.locator('button:has-text("6h"), a:has-text("6h")').first
                if await renew_btn.is_visible():
                    await renew_btn.click()
                    await asyncio.sleep(5)
                    send_tg_msg("🚀 **大功告成！服务器已成功延长 6 小时。**")
                else:
                    await page.screenshot(path=debug_pic)
                    send_tg_msg("⚠️ 登录成功但没找到续期按钮，请看截图确认。")
            else:
                await page.screenshot(path=debug_pic)
                title = await page.title()
                send_tg_msg(f"❌ **卡在验证码界面**\n标题: {title}\n程序已尽力，请尝试手动过一次验证码让 IP 变白。")

        except Exception as e:
            await page.screenshot(path=debug_pic)
            send_tg_msg(f"🔥 运行崩溃: `{str(e)[:100]}`")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
