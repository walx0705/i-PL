import os
import asyncio
import requests
import random
from playwright.async_api import async_playwright

def send_tg_msg(message):
    token = os.environ.get('TG_BOT_TOKEN')
    chat_id = os.environ.get('TG_CHAT_ID')
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": f"🤖 **IceHost 续期助手**\n\n{message}", "parse_mode": "Markdown"}
        try: requests.post(url, data=data, timeout=10)
        except: pass

def send_tg_photo(photo_path, caption):
    token = os.environ.get('TG_BOT_TOKEN')
    chat_id = os.environ.get('TG_CHAT_ID')
    if token and chat_id and os.path.exists(photo_path):
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        try:
            with open(photo_path, 'rb') as photo:
                requests.post(url, files={'photo': photo}, data={'chat_id': chat_id, 'caption': caption}, timeout=15)
        except: pass

async def run():
    async with async_playwright() as p:
        # 1. 启动浏览器（带 SOCKS5 代理）
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": "socks5://127.0.0.1:1080"}
        )
        
        # 2. 深度模拟手机指纹
        context = await browser.new_context(
            viewport={'width': 390, 'height': 844}, # iPhone 14 尺寸
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale="zh-CN",
            timezone_id="Asia/Shanghai"
        )
        
        # 注入脚本隐藏自动化特征
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        debug_pic = "check.png"

        try:
            # 随机起始等待
            await asyncio.sleep(random.uniform(2, 5))
            
            print("正在尝试访问登录页...")
            # 增加超时时间，处理加载慢的问题
            await page.goto("https://dash.icehost.pl/login", timeout=100000, wait_until="load")
            
            # 关键：给 Cloudflare 留出足够的检测时间
            await asyncio.sleep(12) 
            
            # 截图看状态
            await page.screenshot(path=debug_pic)

            email_field = page.locator('input[name="email"]')
            if await email_field.is_visible():
                print("成功发现登录框，开始登录...")
                await email_field.fill(os.environ['ICE_EMAIL'])
                await asyncio.sleep(random.uniform(1, 2))
                await page.fill('input[name="password"]', os.environ['ICE_PASSWORD'])
                await asyncio.sleep(random.uniform(1, 2))
                
                await page.click('button[type="submit"]')
                await page.wait_for_url("**/dashboard", timeout=30000)
                
                # 进入服务器管理
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                await asyncio.sleep(6)

                btn = page.get_by_text("增加6小时的有效期")
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(4)
                    await page.screenshot(path=debug_pic)
                    send_tg_photo(debug_pic, "✅ 续期指令已发送")
                else:
                    await page.screenshot(path=debug_pic)
                    send_tg_photo(debug_pic, "⚠️ 未发现按钮 (可能冷却中)")
            else:
                title = await page.title()
                send_tg_photo(debug_pic, f"❌ 仍然拦截\n标题: {title}")
                send_tg_msg("目前的代理 IP 可能被 IceHost 对非移动端设备进行了限制，请尝试更换节点。")

        except Exception as e:
            print(f"Error: {e}")
            send_tg_msg(f"🔥 执行异常: `{str(e)[:50]}`")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
