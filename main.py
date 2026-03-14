import os
import asyncio
import requests
from playwright.async_api import async_playwright

# --- 配置区 ---
# 建议在 GitHub Secrets 中设置这些变量
ICE_EMAIL = os.environ.get('ICE_EMAIL')
ICE_PASSWORD = os.environ.get('ICE_PASSWORD')
TG_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')
# 代理地址需与 YAML 文件中的配置保持一致
PROXY_SERVER = "socks5://127.0.0.1:1080"

def send_tg_msg(message):
    if TG_TOKEN and TG_CHAT_ID:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": f"🤖 **IceHost 续期助手**\n\n{message}", "parse_mode": "Markdown"}
        try:
            requests.post(url, data=data, timeout=10)
        except Exception as e:
            print(f"发送TG文本失败: {e}")

def send_tg_photo(photo_path, caption):
    if TG_TOKEN and TG_CHAT_ID and os.path.exists(photo_path):
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        try:
            with open(photo_path, 'rb') as photo:
                requests.post(url, files={'photo': photo}, data={'chat_id': TG_CHAT_ID, 'caption': caption}, timeout=15)
        except Exception as e:
            print(f"发送TG图片失败: {e}")

async def run_renewal():
    async with async_playwright() as p:
        # 启动带代理的浏览器
        print(f"正在启动浏览器，使用代理: {PROXY_SERVER}")
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": PROXY_SERVER}
        )
        
        # 模拟真实的 iPhone 浏览器指纹，进一步降低被墙概率
        context = await browser.new_context(
            viewport={'width': 390, 'height': 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            locale="en-US",
            timezone_id="Europe/Warsaw" # 匹配你节点的波兰时区
        )
        
        page = await context.new_page()
        msg = ""
        debug_pic = "result.png"

        try:
            # 1. 访问登录页面
            print("正在访问 IceHost 登录页...")
            await page.goto("https://dash.icehost.pl/login", wait_until="load", timeout=90000)
            await asyncio.sleep(8) # 等待 Cloudflare 盾牌通过

            # 2. 填写登录信息
            email_field = page.locator('input[name="email"]')
            if await email_field.is_visible():
                await email_field.fill(ICE_EMAIL)
                await page.fill('input[name="password"]', ICE_PASSWORD)
                await page.click('button[type="submit"]')
                
                # 等待登录成功的标识（dashboard 出现）
                await page.wait_for_url("**/dashboard", timeout=30000)
                print("登录成功！")

                # 3. 跳转到服务器管理页
                # 你的服务器 ID: bfe8ebd5
                await page.goto("https://dash.icehost.pl/server/bfe8ebd5", wait_until="networkidle")
                await asyncio.sleep(5)

                # 4. 执行续期点击
                # 查找包含指定文字的按钮
                renew_btn = page.get_by_text("增加6小时的有效期")
                
                if await renew_btn.is_visible():
                    await renew_btn.click()
                    await asyncio.sleep(5) # 等待点击后的反馈
                    
                    # 检查是否有红色错误弹窗（比如冷却中）
                    error_msg = page.locator('.alert-danger, .error-message')
                    if await error_msg.is_visible():
                        content = await error_msg.inner_text()
                        msg = f"❌ **续期未成功**\n官方提示: `{content.strip()}`"
                    else:
                        msg = "✅ **续期指令已发送**\n请查看下方截图确认状态。"
                else:
                    msg = "⚠️ **未发现续期按钮**\n可能当前已经在冷却中，或者按钮文本已变更。"
            else:
                title = await page.title()
                msg = f"❌ **无法进入登录页**\n当前页面标题: `{title}`\n可能代理失效或被拦截。"

            # 无论结果如何，保存一张截图
            await page.screenshot(path=debug_pic, full_page=True)
            send_tg_photo(debug_pic, "运行现场截图")

        except Exception as e:
            await page.screenshot(path=debug_pic)
            send_tg_photo(debug_pic, f"异常截图: {str(e)[:50]}")
            msg = f"🔥 **执行异常**\n错误简报: `{str(e)[:100]}`"
        
        finally:
            send_tg_msg(msg)
            await browser.close()

if __name__ == "__main__":
    if not all([ICE_EMAIL, ICE_PASSWORD, TG_TOKEN, TG_CHAT_ID]):
        print("错误: 请确保所有 GitHub Secrets (EMAIL, PASSWORD, TG_TOKEN, TG_CHAT_ID) 已配置。")
    else:
        asyncio.run(run_renewal())
