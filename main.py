import os
import asyncio
import sys
import requests
from playwright.async_api import async_playwright

# --- 配置 ---
# 直接使用你提供的具体服务器地址
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
        res = requests.post(url, json={"chat_id": tg_id, "text": message}, timeout=10)
        print(f"TG 响应: {res.status_code}, {res.text}")
    except Exception as e:
        print(f"TG 发送异常: {e}")

async def run_task():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # 1. 注入 Cookie (修复 Protocol error: Invalid cookie fields)
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            formatted_cookies = []
            clean_raw = raw_cookies.replace('\n', '').replace('\r', '').strip()
            # 兼容带等号或不带等号的各种格式
            for item in clean_raw.split(';'):
                if '=' in item:
                    parts = item.strip().split('=', 1)
                    name = parts[0].strip()
                    value = parts[1].strip()
                    if name and value:
                        formatted_cookies.append({
                            'name': name, 'value': value,
                            'domain': 'dash.icehost.pl', 'path': '/',
                            'secure': True, 'sameSite': 'Lax'
                        })
            try:
                await context.add_cookies(formatted_cookies)
                print(f"✅ 成功注入 {len(formatted_cookies)} 条 Cookie")
            except Exception as e:
                print(f"❌ Cookie 注入失败: {e}")

        page = await context.new_page()

        try:
            print(f"🚀 正在访问直接地址: {BASE_URL}")
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)

            # 2. 备用登录
            if await page.query_selector('input[name="username"]'):
                print("⚠️ Cookie 可能已失效，尝试账号密码登录...")
                email = os.environ.get("PTERODACTYL_EMAIL")
                pw = os.environ.get("PTERODACTYL_PASSWORD")
                if email and pw:
                    await page.fill('input[name="username"]', email)
                    await page.fill('input[name="password"]', pw)
                    await page.click('button[type="submit"]')
                    await page.wait_for_load_state("networkidle")

            # 3. 寻找并点击
            print(f"🔍 正在寻找续期按钮...")
            # 增加一点等待时间确保页面加载完
            await asyncio.sleep(5)
            
            # 使用更稳健的文字匹配
            selector = f"text='{RENEW_BUTTON_TEXT}'"
            btn = await page.query_selector(selector)
            
            if btn:
                await btn.click()
                success_msg = "✅ IceHost 服务器续期成功！"
                print(success_msg)
                send_tg_msg(success_msg)
                await asyncio.sleep(3)
                await page.screenshot(path="success.png")
            else:
                # 检查是否已经是续期过的状态
                content = await page.content()
                if "2026-03" in content:
                    print("ℹ️ 按钮未出现，但从页面日期看似乎已经续期过了。")
                else:
                    print("❌ 未找到续期按钮，请检查 Cookie 是否过期。")
                await page.screenshot(path="not_found.png")

        except Exception as e:
            err_msg = f"🚨 脚本执行出错: {str(e)}"
            print(err_msg)
            send_tg_msg(err_msg)
            await page.screenshot(path="error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_task())
