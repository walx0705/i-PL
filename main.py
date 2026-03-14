import os
import asyncio
import requests
import random
from playwright.async_api import async_playwright

# --- 环境变量配置 ---
ICE_EMAIL = os.environ.get('ICE_EMAIL')
ICE_PASSWORD = os.environ.get('ICE_PASSWORD')
TG_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')
PROXY_SERVER = "socks5://127.0.0.1:1080"

def send_tg_msg(message):
    if TG_TOKEN and TG_CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": f"🤖 **IceHost 自动续期(Stealth)**\n\n{message}", "parse_mode": "Markdown"}
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
        # 1. 启动浏览器并加载 Hy2 代理
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY_SERVER})
        
        # 2. 模拟真实 iPhone 15 指纹，绕过基础识别
        context = await browser.new_context(
            viewport={'width': 393, 'height': 852},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            is_mobile=True,
            has_touch=True,
            locale="zh-CN",
            timezone_id="Asia/Shanghai"
        )
        
        # 3. 核心：抹除 Webdriver 自动化特征
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
        """)
        
        page = await context.new_page()
        debug_pic = "run_status.png"

        try:
            print("正在通过 Hy2 隧道闯入登录页...")
            await page.goto("https://dash.icehost.pl/login", wait_until="networkidle", timeout=100000)
            
            # 给验证码和 WAF 留出充足的加载和自动校验时间
            await asyncio.sleep(25) 
            
            # 捕获当前状态截图
            await page.screenshot(path=debug_pic)

            # 定位输入框 (兼容多语言)
            email_field = page.locator('input[name="email"]')
            
            if await email_field.is_visible():
                print("✅ 验证码穿透成功，执行登录...")
                await email_field.fill(ICE_EMAIL)
                await asyncio.sleep(random.uniform(1, 2))
                await page.fill('input[name="password"]', ICE_PASSWORD)
                await asyncio.sleep(1)
                
                # 点击登录按钮
                await page.click('button[type="submit"]')
                await page.wait_for_url("**/dashboard", timeout=45000)
                
                # 进入特定服务器管理页
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                await asyncio.sleep(8)
                
                # 寻找包含 "6h" 文字的续期按钮
                renew_btn = page.get_by_text("6h")
                if await renew_btn.is_visible():
                    await renew_btn.click()
                    await asyncio.sleep(5)
                    send_tg_msg("🚀 **续期请求已提交成功！**")
                else:
                    await page.screenshot(path=debug_pic)
                    send_tg_photo(debug_pic, "⚠️ 登录成功，但未在管理页发现续期按钮")
            else:
                title = await page.title()
                send_tg_photo(debug_pic, f"❌ 仍被验证码卡住\n标题: {title}")
                send_tg_msg("程序已尽力模拟真人。建议你在手机端挂着同一个 Hy2 节点登录一次，以洗白该 IP 的风险值。")

        except Exception as e:
            await page.screenshot(path=debug_pic)
            send_tg_msg(f"🔥 脚本运行崩溃: `{str(e)[:100]}`")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
