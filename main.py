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
        data = {"chat_id": TG_CHAT_ID, "text": f"🤖 **IceHost 强化版助手**\n\n{message}", "parse_mode": "Markdown"}
        try: requests.post(url, data=data, timeout=10)
        except: pass

def send_tg_photo(photo_path, caption):
    if TG_TOKEN and TG_CHAT_ID and os.path.exists(photo_path):
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        try:
            with open(photo_path, 'rb') as photo:
                requests.post(url, files={'photo': photo}, data={'chat_id': TG_CHAT_ID, 'caption': caption}, timeout=15)
        except: pass

async def human_type(element, text):
    """模拟人类打字：每个字符间隔随机"""
    for char in text:
        await element.type(char, delay=random.randint(50, 150))

async def run():
    async with async_playwright() as p:
        # 1. 启动浏览器并混淆 WebDriver 特征
        browser = await p.chromium.launch(
            headless=True, 
            proxy={"server": PROXY_SERVER},
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # 2. 模拟高配 iPhone 15 Pro 的指纹
        context = await browser.new_context(
            viewport={'width': 393, 'height': 852},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1",
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale="en-GB",
            timezone_id="Europe/London"
        )
        
        # 3. 注入脚本：彻底抹除所有机器人痕迹
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', {get: () => ['en-GB', 'en']});
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Apple GPU';
                if (parameter === 37446) return 'Apple A17 GPU';
                return getParameter(parameter);
            };
        """)
        
        page = await context.new_page()
        debug_pic = "final_check.png"

        try:
            # 随机延迟启动
            await asyncio.sleep(random.uniform(3, 7))
            
            print("正在穿透拦截...")
            await page.goto("https://dash.icehost.pl/login", timeout=120000, wait_until="networkidle")
            
            # 模拟随机滚动，迷惑 Cloudflare
            await page.mouse.wheel(0, 300)
            await asyncio.sleep(15) # 给盾牌留足扫描时间
            
            await page.screenshot(path=debug_pic)

            email_field = page.locator('input[name="email"]')
            if await email_field.count() > 0:
                print("发现登录入口，执行模拟人类输入...")
                await email_field.click()
                await human_type(email_field, ICE_EMAIL)
                
                pass_field = page.locator('input[name="password"]')
                await pass_field.click()
                await human_type(pass_field, ICE_PASSWORD)
                
                await asyncio.sleep(random.uniform(1, 2))
                await page.click('button[type="submit"]')
                
                # 等待进入后台
                try:
                    await page.wait_for_url("**/dashboard", timeout=40000)
                    print("登录成功！")
                    
                    # 跳转管理页 (你的具体服务器ID)
                    await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                    await asyncio.sleep(8)
                    
                    # 尝试多种选择器查找按钮
                    renew_btn = page.locator('button:has-text("增加6小时的有效期"), .btn:has-text("增加6小时")').first
                    
                    if await renew_btn.is_visible():
                        await renew_btn.click()
                        await asyncio.sleep(5)
                        await page.screenshot(path=debug_pic)
                        send_tg_photo(debug_pic, "✅ 续期执行完毕")
                        send_tg_msg("🚀 续期请求已提交成功！")
                    else:
                        await page.screenshot(path=debug_pic)
                        send_tg_photo(debug_pic, "⚠️ 页面已加载但未发现按钮")
                        send_tg_msg("可能按钮文字变了，或者当前还没到续期时间。")
                except:
                    await page.screenshot(path=debug_pic)
                    send_tg_photo(debug_pic, "❌ 登录后未能跳转后台")
            else:
                title = await page.title()
                send_tg_photo(debug_pic, f"❌ 依然被封\n标题: {title}")
                send_tg_msg("Cloudflare 依然识别出了 Actions 环境。这通常意味着该 Vless 节点的出口 IP 段被精准封锁了。建议换一个不同地区的节点再试。")

        except Exception as e:
            await page.screenshot(path=debug_pic)
            send_tg_photo(debug_pic, f"🔥 崩溃快照: {str(e)[:40]}")
            send_tg_msg(f"🔥 运行崩溃: `{str(e)[:100]}`")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
