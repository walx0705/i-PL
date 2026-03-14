import os
import asyncio
import requests
import random
from playwright.async_api import async_playwright

# --- 配置从 Secrets 读取 ---
ICE_EMAIL = os.environ.get('ICE_EMAIL')
ICE_PASSWORD = os.environ.get('ICE_PASSWORD')
TG_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

def send_tg_msg(message):
    if TG_TOKEN and TG_CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": f"🤖 **IceHost 续期(Hy2)**\n\n{message}", "parse_mode": "Markdown"}
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
        # 强制连接 Hy2 开启的 1080 端口
        print("启动浏览器并挂载本地 Hy2 代理...")
        browser = await p.chromium.launch(
            headless=True, 
            proxy={"server": "socks5://127.0.0.1:1080"}
        )
        
        # 深度伪装手机端
        context = await browser.new_context(
            viewport={'width': 393, 'height': 852},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            is_mobile=True,
            has_touch=True
        )
        
        page = await context.new_page()
        debug_pic = "hy2_status.png"

        try:
            # 随机延迟增加真实感
            await asyncio.sleep(random.uniform(5, 10))
            
            print("尝试访问登录页...")
            await page.goto("https://dash.icehost.pl/login", timeout=120000, wait_until="load")
            
            # Cloudflare 盾牌穿透等待
            await asyncio.sleep(20) 
            await page.screenshot(path=debug_pic)

            email_field = page.locator('input[name="email"]')
            if await email_field.count() > 0:
                print("代理成功，正在登录...")
                await email_field.fill(ICE_EMAIL)
                await page.fill('input[name="password"]', ICE_PASSWORD)
                await page.click('button[type="submit"]')
                
                await page.wait_for_url("**/dashboard", timeout=40000)
                
                # 进入服务器续期页
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                await asyncio.sleep(8)
                
                # 寻找续期按钮
                btn = page.get_by_text("增加6小时的有效期")
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(5)
                    await page.screenshot(path=debug_pic)
                    send_tg_photo(debug_pic, "✅ Hy2 通道续期成功")
                else:
                    await page.screenshot(path=debug_pic)
                    send_tg_photo(debug_pic, "⚠️ 登录成功但未发现按钮")
            else:
                title = await page.title()
                send_tg_photo(debug_pic, f"❌ Hy2 代理后仍被拦截\n标题: {title}")
                send_tg_msg("这个 Hy2 节点的 IP 恐怕也被 IceHost WAF 标记了。")

        except Exception as e:
            send_tg_msg(f"🔥 运行错误: `{str(e)[:100]}`")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
