import os
import asyncio
import sys
import requests
from playwright.async_api import async_playwright

# --- 配置 ---
BASE_URL = "https://icehost.pl" 
RENEW_BUTTON_TEXT = "DODAJ 6 GODZIN WAŻNOŚCI"

def send_tg_msg(message):
    tg_token = os.environ.get("TG_TOKEN")
    tg_id = os.environ.get("TG_CHAT_ID")
    if tg_token and tg_id:
        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": tg_id, "text": message}, timeout=10)
        except Exception as e:
            print(f"TG通知失败: {e}")

async def run_task():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # 1. 强化 Cookie 注入逻辑（修复 Invalid cookie fields）
        raw_cookies = os.environ.get("PTERODACTYL_COOKIE", "")
        if raw_cookies:
            print("正在清洗并注入 Cookie...")
            formatted_cookies = []
            # 移除换行，按分号分割
            items = raw_cookies.replace('\n', '').replace('\r', '').split(';')
            
            for item in items:
                if '=' in item:
                    # 关键修复：彻底移除键值对两端的空格
                    parts = item.split('=', 1)
                    name = parts[0].strip()
                    value = parts[1].strip()
                    
                    if name and value:
                        formatted_cookies.append({
                            'name': name,
                            'value': value,
                            'domain': 'icehost.pl',
                            'path': '/',
                            'secure': True,
                            'sameSite': 'Lax'
                        })

            if formatted_cookies:
                try:
                    await context.add_cookies(formatted_cookies)
                    print(f"✅ 成功注入 {len(formatted_cookies)} 条核心 Cookie")
                except Exception as e:
                    print(f"⚠️ Cookie 部分注入失败 (Protocol Error): {e}")

        page = await context.new_page()

        try:
            print(f"🚀 访问面板: {BASE_URL}")
            # 使用 networkidle 确保加载完全
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)

            # 2. 自动登录补丁
            if await page.query_selector('input[name="username"]'):
                print("⚠️ Cookie 已失效或未生效，尝试账号登录...")
                email = os.environ.get("PTERODACTYL_EMAIL")
                pw = os.environ.get("PTERODACTYL_PASSWORD")
                if email and pw:
                    await page.fill('input[name="username"]', email)
                    await page.fill('input[name="password"]', pw)
                    await page.click('button[type="submit"]')
                    await page.wait_for_load_state("networkidle")
                else:
                    print("❌ 无法登录：缺少 EMAIL 或 PASSWORD Secrets")

            # 3. 按钮点击
            print(f"🔍 正在寻找: {RENEW_BUTTON_TEXT}")
            # 使用 XPath 增加定位成功率
            try:
                btn = await page.wait_for_selector(f'text="{RENEW_BUTTON_TEXT}"', timeout=20000)
                if btn:
                    await btn.click()
                    print("✅ 续期按钮点击成功！")
                    send_tg_msg("✅ IceHost 续期成功！")
                    await asyncio.sleep(5)
                    await page.screenshot(path="success.png")
                else:
                    print("❌ 页面未发现续期按钮。")
                    await page.screenshot(path="no_button.png")
            except Exception:
                print("⚠️ 定位超时，可能按钮文字不匹配或已在倒计时中。")
                await page.screenshot(path="timeout.png")

        except Exception as e:
            print(f"🚨 脚本异常: {e}")
            if 'page' in locals():
                await page.screenshot(path="fatal_error.png")
            send_tg_msg(f"🚨 IceHost 运行异常: {str(e)}")
            sys.exit(1)
        finally:
            await browser.close()
            print("🏁 任务结束。")

if __name__ == "__main__":
    asyncio.run(run_task())
