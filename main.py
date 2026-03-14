import os
import asyncio
import requests
import random
from playwright.async_api import async_playwright

# --- 配置 ---
ICE_EMAIL = os.environ.get('ICE_EMAIL')
ICE_PASSWORD = os.environ.get('ICE_PASSWORD')
TG_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')
PROXY_SERVER = "socks5://127.0.0.1:1080"

def send_tg_msg(message):
    if TG_TOKEN and TG_CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": f"🤖 **IceHost 续期(Hy2成功版)**\n\n{message}", "parse_mode": "Markdown"}
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
        # 使用 Hy2 开启的本地代理
        browser = await p.chromium.launch(
            headless=True, 
            proxy={"server": PROXY_SERVER}
        )
        
        context = await browser.new_context(
            viewport={'width': 393, 'height': 852},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            is_mobile=True,
            has_touch=True
        )
        
        page = await context.new_page()
        debug_pic = "step_result.png"

        try:
            print("正在通过 Hy2 隧道访问...")
            # 访问登录页
            await page.goto("https://dash.icehost.pl/login", timeout=120000)
            
            # 关键优化：等待邮箱输入框出现
            try:
                email_input = page.locator('input[name="email"]')
                await email_input.wait_for(state="visible", timeout=45000)
                print("✅ 已定位到登录框")
            except:
                title = await page.title()
                await page.screenshot(path=debug_pic)
                send_tg_photo(debug_pic, f"❌ 未能定位输入框\n标题: {title}")
                return

            # 执行登录逻辑
            await email_input.fill(ICE_EMAIL)
            await asyncio.sleep(1)
            await page.fill('input[name="password"]', ICE_PASSWORD)
            await asyncio.sleep(1)
            
            # 点击登录按钮 (Zaloguj się)
            await page.click('button[type="submit"]')
            
            # 等待进入后台
            await page.wait_for_url("**/dashboard", timeout=45000)
            print("🎉 登录成功！")
            
            # 跳转续期页 (bfe8ebd5)
            await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
            await asyncio.sleep(8)
            
            # 寻找续期按钮并点击
            renew_btn = page.get_by_text("增加6小时的有效期")
            if await renew_btn.is_visible():
                await renew_btn.click()
                await asyncio.sleep(5)
                await page.screenshot(path=debug_pic)
                send_tg_photo(debug_pic, "✅ 续期操作完成")
                send_tg_msg("🚀 恭喜！服务器已成功延长 6 小时。")
            else:
                await page.screenshot(path=debug_pic)
                send_tg_photo(debug_pic, "⚠️ 未发现按钮 (可能冷却中)")
                
        except Exception as e:
            await page.screenshot(path=debug_pic)
            send_tg_photo(debug_pic, f"🔥 运行异常截图")
            send_tg_msg(f"🔥 报错简报: `{str(e)[:100]}`")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
