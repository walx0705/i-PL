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
        data = {"chat_id": TG_CHAT_ID, "text": f"🤖 **IceHost 强力过盾版**\n\n{message}", "parse_mode": "Markdown"}
        try: requests.post(url, data=data, timeout=10)
        except: pass

async def run():
    async with async_playwright() as p:
        # 启动参数优化：禁用自动化特征，开启反检测
        browser = await p.chromium.launch(
            headless=True, 
            proxy={"server": PROXY_SERVER},
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-infobars'
            ]
        )
        
        # 模拟高分屏桌面环境，这比模拟手机在 Actions 里的稳定性更高
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # 核心：注入深度反检测脚本
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en-US', 'en']});
        """)
        
        page = await context.new_page()
        debug_pic = "shield_bypass.png"

        try:
            print("正在强行穿透 Cloudflare...")
            # 使用 commit 模式，只要握手成功就开始注入，不给盾牌反应用的时间
            await page.goto("https://dash.icehost.pl/login", wait_until="commit", timeout=120000)
            
            # 暴力等待 25 秒给 JS 挑战
            await asyncio.sleep(25)
            
            # 循环注入探测
            success_input = False
            for i in range(20):
                print(f"注入尝试 {i+1}/20...")
                try:
                    # 模拟真实的鼠标轨迹移动到邮箱框
                    email_box = page.locator('input[name="email"]')
                    if await email_box.is_visible():
                        box = await email_box.bounding_box()
                        await page.mouse.move(box['x'] + 5, box['y'] + 5, steps=10)
                        await email_box.click()
                        
                        # 模拟慢速输入
                        await page.keyboard.type(ICE_EMAIL, delay=random.randint(50, 150))
                        await page.keyboard.press("Tab")
                        await page.keyboard.type(ICE_PASSWORD, delay=random.randint(50, 150))
                        
                        # 移动到提交按钮并点击
                        submit_btn = page.locator('button[type="submit"]')
                        btn_box = await submit_btn.bounding_box()
                        await page.mouse.move(btn_box['x'] + 10, btn_box['y'] + 10, steps=10)
                        await submit_btn.click()
                        
                        success_input = True
                        break
                except:
                    pass
                await asyncio.sleep(3)

            if success_input:
                # 等待后台跳转
                try:
                    await page.wait_for_url("**/dashboard", timeout=40000)
                    print("🎉 突破重围，登录成功！")
                    
                    # 续期逻辑
                    await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                    await asyncio.sleep(10)
                    await page.get_by_text("6h").click()
                    send_tg_msg("🚀 **过盾强攻成功，续期已完成！**")
                except:
                    await page.screenshot(path=debug_pic)
                    send_tg_msg("❌ 填表已提交，但未能跳转 Dashboard，可能盾牌拦截了 POST 请求。")
            else:
                await page.screenshot(path=debug_pic)
                send_tg_msg("❌ 页面超时或未能在盾牌后找到表单。")

        except Exception as e:
            send_tg_msg(f"🔥 运行异常: `{str(e)[:100]}`")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
