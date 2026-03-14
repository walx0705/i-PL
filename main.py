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
        data = {"chat_id": TG_CHAT_ID, "text": f"🤖 **IceHost 续期(最终点击版)**\n\n{message}", "parse_mode": "Markdown"}
        try: requests.post(url, data=data, timeout=10)
        except: pass

def send_tg_photo(photo_path, caption):
    if TG_TOKEN and TG_CHAT_ID and os.path.exists(photo_path):
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        try:
            with open(photo_path, 'rb') as photo:
                requests.post(url, files={'photo': photo}, data={'chat_id': TG_CHAT_ID, 'caption': caption}, timeout=15)
        except: pass

async def run():
    async with async_playwright() as p:
        # 启动浏览器，关闭自动化标志
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY_SERVER})
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        # 深度注入：防止被识别为 Playwright
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)
        
        page = await context.new_page()
        debug_pic = "final_check.png"

        try:
            print("正在访问登录页...")
            await page.goto("https://dash.icehost.pl/login", wait_until="networkidle", timeout=90000)
            await asyncio.sleep(10) # 等待验证码框加载

            # 1. 尝试处理那个“打勾”的 reCAPTCHA 复选框
            try:
                # 寻找验证码所在的 iframe
                captcha_frame = page.frame_locator('iframe[title*="reCAPTCHA"]')
                checkbox = captcha_frame.locator('#recaptcha-anchor')
                if await checkbox.is_visible():
                    print("发现打勾选项，尝试点击...")
                    await checkbox.click()
                    await asyncio.sleep(5) # 点击后等待验证通过
            except Exception as e:
                print(f"验证码自动处理跳过或失败: {e}")

            # 2. 定位输入框
            email_field = page.locator('input[name="email"]')
            if await email_field.is_visible():
                print("✅ 成功定位，开始登录...")
                await email_field.fill(ICE_EMAIL)
                await page.fill('input[name="password"]', ICE_PASSWORD)
                
                # 点击登录
                await page.click('button[type="submit"]')
                
                # 3. 等待并跳转后台
                await page.wait_for_url("**/dashboard", timeout=45000)
                print("🎉 登录成功，进入后台")
                
                # 跳转服务器页面 (bfe8ebd5)
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                await asyncio.sleep(8)
                
                # 点击续期按钮
                renew_btn = page.locator('button:has-text("6h"), .btn:has-text("6h")').first
                if await renew_btn.is_visible():
                    await renew_btn.click()
                    await asyncio.sleep(3)
                    send_tg_msg("🚀 **服务器续期已提交！**")
                else:
                    await page.screenshot(path=debug_pic)
                    send_tg_photo(debug_pic, "⚠️ 登录成功但没找到续期按钮")
            else:
                await page.screenshot(path=debug_pic)
                send_tg_photo(debug_pic, "❌ 依然卡在验证界面，请看图")
                send_tg_msg("脚本已尝试点击‘打勾’，但可能触发了图片验证。建议更换一个 IP 更干净的节点。")

        except Exception as e:
            await page.screenshot(path=debug_pic)
            send_tg_msg(f"🔥 执行异常: `{str(e)[:100]}`")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
