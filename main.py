import os
import asyncio
import requests
from playwright.async_api import async_playwright

def send_tg_msg(message):
    token = os.environ.get('TG_BOT_TOKEN')
    chat_id = os.environ.get('TG_CHAT_ID')
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": f"🤖 **IceHost 续期助手**\n\n{message}", "parse_mode": "Markdown"}
        try:
            requests.post(url, data=data, timeout=10)
        except:
            pass

async def run():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=True)
        # 深度伪装：模拟 iPhone 环境
        context = await browser.new_context(
            viewport={'width': 390, 'height': 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            locale="zh-CN",
            timezone_id="Asia/Shanghai"
        )
        page = await context.new_page()
        msg = ""

        try:
            print("正在尝试穿透 Cloudflare...")
            # 访问登录页，允许最长 2 分钟加载
            await page.goto("https://dash.icehost.pl/login", wait_until="commit", timeout=120000)
            
            # 关键：静止 15 秒，让 Cloudflare 的检查脚本跑完
            await asyncio.sleep(15)

            # 检查是否看到了邮箱输入框
            email_field = page.locator('input[name="email"]')
            if await email_field.is_visible():
                await email_field.fill(os.environ['ICE_EMAIL'])
                await page.fill('input[name="password"]', os.environ['ICE_PASSWORD'])
                await page.click('button[type="submit"]')
                
                # 等待登录后的页面加载
                await page.wait_for_url("**/dashboard", timeout=30000)
                
                # 直接跳转续期地址
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                await asyncio.sleep(5)

                # 执行续期点击
                renew_btn = page.get_by_text("增加6小时的有效期")
                if await renew_btn.is_visible():
                    await renew_btn.click()
                    await asyncio.sleep(3)
                    msg = "✅ **续期操作完成**\n请检查剩余时间或 TG 报错截图。"
                else:
                    msg = "⚠️ **按钮未发现**\n可能处于冷却期，或页面加载不全。"
            else:
                title = await page.title()
                msg = f"❌ **拦截失败**\n页面停留在了: `{title}`\n这通常是 Cloudflare 盾牌太厚，GitHub 无法进入。"

        except Exception as e:
            msg = f"🔥 **运行超时**\n网络环境较差，页面未能按时加载。"
        finally:
            send_tg_msg(msg)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
