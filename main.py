import os
import asyncio
import requests
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
        data = {"chat_id": TG_CHAT_ID, "text": f"🤖 **IceHost 最终盲填版**\n\n{message}", "parse_mode": "Markdown"}
        try: requests.post(url, data=data, timeout=10)
        except: pass

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy={"server": PROXY_SERVER})
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            viewport={'width': 393, 'height': 852},
            is_mobile=True
        )
        
        # 彻底抹除 WebDriver 特征
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        debug_pic = "force_result.png"

        try:
            print("正在连接登录页面...")
            await page.goto("https://dash.icehost.pl/login", wait_until="commit", timeout=90000)
            
            # --- 循环探测注入 (解决 Cannot set properties of null) ---
            login_success = False
            for i in range(30):  # 最多等待 60 秒 (2s * 30)
                print(f"等待输入框出现... ({i+1}/30)")
                # 使用 JS 探测并填表
                try:
                    res = await page.evaluate(f"""
                        (function() {{
                            const e = document.querySelector('input[name="email"]');
                            const p = document.querySelector('input[name="password"]');
                            const b = document.querySelector('button[type="submit"]');
                            if (e && p && b) {{
                                e.value = '{ICE_EMAIL}';
                                p.value = '{ICE_PASSWORD}';
                                b.click();
                                return "OK";
                            }}
                            return "WAIT";
                        }})()
                    """)
                    if res == "OK":
                        print("✅ 探测到输入框，已强行注入！")
                        login_success = True
                        break
                except:
                    pass
                await asyncio.sleep(2)
            
            if not login_success:
                await page.screenshot(path=debug_pic)
                send_tg_msg("❌ 60秒内未发现登录框，可能是被 Cloudflare 彻底拦截了。")
                return

            # 等待进入后台
            try:
                await page.wait_for_url("**/dashboard", timeout=40000)
                print("🎉 登录成功！")
                
                # 续期流程
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5")
                await asyncio.sleep(10)
                
                # 点击 6h
                renew_btn = page.locator('button:has-text("6h"), a:has-text("6h")').first
                if await renew_btn.is_visible():
                    await renew_btn.click()
                    await asyncio.sleep(5)
                    send_tg_msg("🚀 **全自动强攻续期成功！**")
                else:
                    await page.screenshot(path=debug_pic)
                    send_tg_msg("⚠️ 登录成功，但未发现续期按钮。")
            except:
                await page.screenshot(path=debug_pic)
                send_tg_msg("❌ 填表已提交，但未能进入后台，请看截图。")

        except Exception as e:
            send_tg_msg(f"🔥 最终强攻异常: `{str(e)[:100]}`")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
