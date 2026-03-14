import os
import asyncio
import sys
import requests
from playwright.async_api import async_playwright

# --- 配置 ---
BASE_URL = "https://dash.icehost.pl/server/bfe8ebd5" 
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"

def send_tg_msg(message):
    tg_token = os.environ.get("TG_TOKEN")
    tg_id = os.environ.get("TG_CHAT_ID")
    if not tg_token or not tg_id:
        print("⚠️ TG 配置缺失，跳过通知")
        return
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": tg_id, "text": message}, timeout=15)
        print(f"TG 响应: {res.status_code}")
    except Exception as e:
        print(f"TG 发送异常: {e}")

async def run_task():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        # 注入 Cookie
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            formatted_cookies = []
            clean_raw = raw_cookies.replace('\n', '').replace('\r', '').strip()
            for item in clean_raw.split(';'):
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    formatted_cookies.append({
                        'name': name.strip(), 'value': value.strip(),
                        'domain': 'dash.icehost.pl', 'path': '/',
                        'secure': True, 'sameSite': 'Lax'
                    })
            await context.add_cookies(formatted_cookies)

        page = await context.new_page()
        # 设置全局超时为 90 秒
        page.set_default_timeout(90000)

        try:
            print(f"🚀 正在访问 (尝试绕过网络波动): {BASE_URL}")
            # 关键修改：将 networkidle 改为 domcontentloaded，加快响应
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=90000)
            
            # 给一点额外缓冲时间让脚本加载
            await asyncio.sleep(10)

            # 检查是否跳到了登录页
            if await page.query_selector('input[name="username"]'):
                print("⚠️ Cookie 失效，尝试账号密码登录...")
                email = os.environ.get("PTERODACTYL_EMAIL")
                pw = os.environ.get("PTERODACTYL_PASSWORD")
                if email and pw:
                    await page.fill('input[name="username"]', email)
                    await page.fill('input[name="password"]', pw)
                    await page.click('button[type="submit"]')
                    await page.wait_for_load_state("domcontentloaded")
                    await asyncio.sleep(5)

            # 寻找并点击续期按钮
            print(f"🔍 寻找按钮: {RENEW_BUTTON_TEXT}")
            # 尝试通过 text 寻找按钮
            btn = page.get_by_text(RENEW_BUTTON_TEXT)
            
            if await btn.count() > 0:
                await btn.first.click()
                success_msg = "✅ IceHost 续期动作已触发！"
                print(success_msg)
                send_tg_msg(success_msg)
                await asyncio.sleep(5)
                await page.screenshot(path="success.png")
            else:
                # 日期判定逻辑：如果找不到按钮，看看页面上是不是已经有 2026 年的日期了
                content = await page.content()
                if "2026-03" in content:
                    print("ℹ️ 未发现按钮，但页面显示已续期。")
                else:
                    print("❌ 未找到按钮，且未发现续期成功迹象。")
                await page.screenshot(path="not_found.png")

        except Exception as e:
            err_msg = f"🚨 运行超时或出错: {str(e)[:100]}"
            print(err_msg)
            send_tg_msg(err_msg)
            await page.screenshot(path="error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_task())
