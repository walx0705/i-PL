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
        data = {"chat_id": TG_CHAT_ID, "text": f"🤖 **IceHost 续期(环境同步版)**\n\n{message}", "parse_mode": "Markdown"}
        try: requests.post(url, data=data, timeout=10)
        except: pass

async def run():
    async with async_playwright() as p:
        # 1. 模拟真实浏览器，移除所有自动化特征
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY_SERVER})
        
        # 2. 使用和你手机完全一致的 UA 和配置
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            viewport={'width': 393, 'height': 852},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale="zh-CN",
            timezone_id="Asia/Shanghai"
        )
        
        # 3. 注入关键脚本：彻底抹除 Playwright 痕迹
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
            navigator.languages = ['zh-CN', 'zh'];
        """)
        
        page = await context.new_page()
        debug_pic = "final_attempt.png"

        try:
            print("正在以手机模式访问...")
            # 增加随机等待，模拟真实人类打开网页
            await asyncio.sleep(random.uniform(2, 5))
            await page.goto("https://dash.icehost.pl/login", wait_until="networkidle", timeout=90000)
            
            # 4. 关键：不要急着找框，先模拟人类滑动一下页面，触发隐形验证通过
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(10)

            # 定位输入框
            email_field = page.locator('input[name="email"]')
            
            if await email_field.is_visible():
                print("✅ 手机模拟成功，开始自动登录...")
                # 模拟慢速打字
                await email_field.type(ICE_EMAIL, delay=random.randint(50, 150))
                await page.fill('input[name="password"]', ICE_PASSWORD)
                
                # 点击登录
                await page.click('button[type="submit"]')
                
                # 5. 等待进入后台
                await page.wait_for_url("**/dashboard", timeout=60000)
                print("🎉 登录成功！")
                
                # 跳转续期页
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                await asyncio.sleep(8)
                
                # 寻找 6h 按钮
                renew_btn = page.get_by_text("6h")
                if await renew_btn.is_visible():
                    await renew_btn.click()
                    await asyncio.sleep(5)
                    send_tg_msg("🚀 **检测到环境同步，续期已完成！**")
                else:
                    await page.screenshot(path=debug_pic)
                    send_tg_msg("⚠️ 已登录，但续期按钮未出现（可能时间还没到）。")
            else:
                await page.screenshot(path=debug_pic)
                send_tg_msg("❌ **Actions 模拟依然被识别**。这说明 Google 记录了 GitHub 的数据中心 IP 段。")

        except Exception as e:
            await page.screenshot(path=debug_pic)
            send_tg_msg(f"🔥 运行中断: `{str(e)[:100]}`")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
