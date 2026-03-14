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
        # 使用更大的延时设置
        browser = await p.chromium.launch(headless=True)
        # 模拟更加真实的浏览器指纹
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        msg = ""

        try:
            print("正在打开登录页面...")
            # 增加超时时间到 60 秒
            await page.goto("https://dash.icehost.pl/login", timeout=60000, wait_until="networkidle")
            
            # 检查是否遇到了 Cloudflare 验证
            if "Cloudflare" in await page.title() or await page.locator('text=Verify you are human').is_visible():
                msg = "🛑 **触发了人机验证 (Cloudflare)**\nGitHub Actions 暂时无法绕过此验证，请稍后再试或手动点击一次。"
            else:
                # 等待输入框出现
                email_input = page.locator('input[name="email"]')
                await email_input.wait_for(state="visible", timeout=30000)
                
                await email_input.fill(os.environ['ICE_EMAIL'])
                await page.fill('input[name="password"]', os.environ['ICE_PASSWORD'])
                
                # 点击登录并等待
                await page.click('button[type="submit"]')
                await page.wait_for_url("**/dashboard", timeout=30000)
                
                # 跳转续期页
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5", wait_until="networkidle")
                
                renew_btn = page.get_by_text("增加6小时的有效期")
                if await renew_btn.is_visible():
                    await renew_btn.click()
                    await asyncio.sleep(5)
                    msg = "✅ **续期指令发送成功**"
                else:
                    msg = "⚠️ **未发现按钮** (可能在冷却中)"

        except Exception as e:
            # 发生错误时尝试抓个图（可选，这里简化为文字反馈）
            msg = f"🔥 **运行异常**\n具体表现: `页面加载超时或元素未找到`\n错误信息: `{str(e)[:100]}`"
        finally:
            send_tg_msg(msg)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
