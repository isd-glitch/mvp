from flask import Flask, request, render_template_string, redirect, url_for, session, Response
import asyncio
import random
from playwright.async_api import async_playwright

app = Flask(__name__)
app.secret_key = 'supersecretkey'
USE_TOR = False

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B)",
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <title>{{ page_title or "Anonymous Proxy" }}</title>
  <style>
    body {
      margin: 0;
      font-family: 'Segoe UI', sans-serif;
      background: radial-gradient(circle at center, #000000, #1a1a1a);
      color: white;
      overflow: hidden;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.3rem 1rem;
      height: 25px;
      background-color: rgba(0,0,0,0.6);
      position: fixed;
      top: 0;
      width: 100%;
      font-size: 0.9rem;
      z-index: 10;
    }
    .form-container {
      margin-top: 20vh;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    input[type="text"] {
      padding: 0.5rem;
      width: 320px;
      border-radius: 5px;
      border: none;
      font-size: 1rem;
    }
    button {
      padding: 0.5rem 1rem;
      margin-left: 0.5rem;
      background: #4682b4;
      color: white;
      border: none;
      border-radius: 5px;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <header>
    <div><strong>Unstoppable Proxy</strong></div>
    <div>
      <form action="/toggle_tor" method="post" style="display:inline;">
        <button type="submit">Tor: {{ 'ON' if use_tor else 'OFF' }}</button>
      </form>
    </div>
  </header>

  <div class="form-container">
    <form action="/browse" method="get">
      <input type="text" name="url" placeholder="https://example.com" required />
      <button type="submit">Go</button>
    </form>
  </div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, use_tor=USE_TOR, page_title="")

@app.route("/toggle_tor", methods=["POST"])
def toggle_tor():
    global USE_TOR
    USE_TOR = not USE_TOR
    return redirect(url_for("home"))

@app.route("/browse")
def browse():
    url = request.args.get("url")
    if not url.startswith("http"):
        url = "https://" + url
    try:
        html = asyncio.run(render_with_js(url))
        return Response(html, mimetype="text/html")
    except Exception as e:
        return f"<h2>Error fetching URL:</h2><pre>{e}</pre>"

async def render_with_js(url):
    user_agent = random.choice(USER_AGENTS)
    with open("stealth.js", "r") as f:
        stealth_script = f.read()

    async with async_playwright() as p:
        args = {"headless": True}
        if USE_TOR:
            args["proxy"] = {"server": "socks5://127.0.0.1:9050"}
        browser = await p.chromium.launch(**args)
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()
        await page.add_init_script(stealth_script)

        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            await browser.close()
            raise e

        await asyncio.sleep(2)
        html = await page.content()
        await browser.close()
        return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
