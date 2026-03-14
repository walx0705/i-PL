import os
import asyncio
import requests
import random
from playwright.async_api import async_playwright

# --- 核心配置 ---
ICE_EMAIL = os.environ.get('ICE_EMAIL')
ICE_PASSWORD = os.environ.get('ICE_PASSWORD')
TG_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')
PROXY_SERVER = "socks5://127.0.0.1:1080"

def send_tg_msg(message):
    if TG_TOKEN and TG_CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": f"🤖 **IceHost 最终全量版**\n\n{message}", "parse_mode": "Markdown"}
        try: requests.post(url, data=data, timeout=10)
        except: pass

async def run():
    async with async_playwright() as p:
        # 1. 启动并混淆底层特征
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY_SERVER})
        
        # 模拟高分辨率显示器，降低机器人特征
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            device_scale_factor=1,
        )
        
        # 核心：注入指纹混淆脚本，抹除 Playwright 痕迹
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
        """)
        
        page = await context.new_page()
        debug_pic = "final_check.png"

        try:
            print("正在尝试穿透保护层...")
            await page.goto("https://dash.icehost.pl/login", wait_until="networkidle", timeout=100000)
            
            # 给验证码和 WAF 盾牌留够 25 秒
            await asyncio.sleep(25)
            
            # 2. 定位输入框并执行“真实模拟”填表
            email_field = page.locator('input[name="email"]')
            if await email_field.is_visible():
                print("✅ 找到表单，开始模拟真人操作...")
                # 点击并打字
                await email_field.click()
                await page.keyboard.type(ICE_EMAIL, delay=random.randint(50, 150))
                
                await page.keyboard.press("Tab")
                await page.keyboard.type(ICE_PASSWORD, delay=random.randint(50, 150))
                
                # 3. 关键：不要直接调用 .click()，而是移动鼠标到按钮坐标点点击
                submit_btn = page.locator('button[type="submit"]')
                box = await submit_btn.bounding_box()
                if box:
                    # 在按钮范围内随机取一个点
                    target_x = box['x'] + box['width'] / 2 + random.randint(-5, 5)
                    target_y = box['y'] + box['height'] / 2 + random.randint(-5, 5)
                    await page.mouse.move(target_x, target_y, steps=10)
                    await page.mouse.click(target_x, target_y)
                
                print("已点击提交，等待后台加载...")
                
                # 4. 验证登录结果
                try:
                    await page.wait_for_url("**/dashboard", timeout=45000)
                    print("🎉 登录成功！正在前往续期页...")
                    
                    await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                    await asyncio.sleep(10)
                    
                    # 续期操作
                    renew_btn = page.get_by_text("6h")
                    if await renew_btn.is_visible():
                        await renew_btn.click()
                        await asyncio.sleep(5)
                        send_tg_msg("🚀 **全量模拟成功，服务器已成功续期！**")
                    else:
                        await page.screenshot(path=debug_pic)
                        send_tg_msg("⚠️ 已登录，但未找到续期按钮（可能还没到时间）。")
                except:
                    await page.screenshot(path=debug_pic)
                    send_tg_msg("❌ 填表已提交，但未检测到后台跳转，可能被 Cloudflare 拦截了。")
            else:
                await page.screenshot(path=debug_pic)
                send_tg_msg("❌ 页面加载超时或输入框未显示，请检查 Hysteria2 节点状态。")

        except Exception as e:
            await page.screenshot(path=debug_pic)
            send_tg_msg(f"🔥 脚本运行中断: `{str(e)[:100]}`")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
