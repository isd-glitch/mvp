from flask import Flask, request, render_template_string, redirect, url_for, session
import asyncio
import random
from playwright.async_api import async_playwright

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # sessionに必要

USE_TOR = False

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36",
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Anonymous Proxy</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            background: {{ 'linear-gradient(to right, #e0eafc, #cfdef3)' if theme == 'light' else 'linear-gradient(to right, #232526, #414345)' }};
            color: {{ '#000' if theme == 'light' else '#f0f0f0' }};
            margin: 0;
            padding-top: 80px;
            animation: fadeBg 2s ease-in-out;
        }
        header {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background: rgba(30, 144, 255, 0.8);
            color: white;
            padding: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            backdrop-filter: blur(8px);
            z-index: 1000;
        }
        .bookmark-bar {
            display: flex;
            gap: 0.5rem;
        }
        .bookmark-bar a {
            color: white;
            background: rgba(0, 0, 0, 0.3);
            padding: 0.3rem 0.7rem;
            border-radius: 5px;
            text-decoration: none;
            font-size: 0.9rem;
        }
        .container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 80vh;
        }
        h1 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            animation: fadeIn 1s ease-in;
        }
        form {
            display: flex;
            gap: 0.5rem;
            animation: slideIn 1s ease-in-out;
            margin: 0.5rem;
        }
        input[type=\"text\"] {
            padding: 0.5rem;
            font-size: 1rem;
            width: 300px;
            border-radius: 8px;
            border: none;
            transition: transform 0.3s ease;
        }
        input[type=\"text\"]:focus {
            transform: scale(1.05);
        }
        button {
            padding: 0.5rem 1rem;
            background: #1e90ff;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.3s ease, transform 0.3s ease;
        }
        button:hover {
            background: #4682b4;
            transform: translateY(-2px);
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes slideIn {
            from { transform: translateY(30px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        @keyframes fadeBg {
            0% { filter: brightness(0.5); }
            100% { filter: brightness(1); }
        }
    </style>
</head>
<body>
    <header>
        <div>Anonymous Proxy</div>
        <div class=\"bookmark-bar\">
            {% for url in bookmarks %}
                <a href=\"/browse?url={{ url }}\">{{ url|truncate(20, True) }}</a>
            {% endfor %}
        </div>
        <div>
            <form action=\"/toggle_tor\" method=\"post\" style=\"display:inline;\">
                <button type=\"submit\">Tor: {{ 'ON' if use_tor else 'OFF' }}</button>
            </form>
            <form action=\"/toggle_theme\" method=\"post\" style=\"display:inline;\">
                <button type=\"submit\">Theme: {{ theme.title() }}</button>
            </form>
        </div>
    </header>
    <div class=\"container\">
        <form action=\"/browse\" method=\"get\">
            <input type=\"text\" name=\"url\" placeholder=\"https://example.com\" required />
            <button type=\"submit\">Go</button>
        </form>
        <form action=\"/bookmark\" method=\"post\">
            <input type=\"text\" name=\"url\" placeholder=\"Bookmark this URL\" required />
            <button type=\"submit\">Bookmark</button>
        </form>
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    global USE_TOR
    if "theme" not in session:
        session["theme"] = "dark"
    if "bookmarks" not in session:
        session["bookmarks"] = []
    return render_template_string(
        HTML_TEMPLATE,
        use_tor=USE_TOR,
        theme=session["theme"],
        bookmarks=session["bookmarks"]
    )

@app.route("/toggle_tor", methods=["POST"])
def toggle_tor():
    global USE_TOR
    USE_TOR = not USE_TOR
    return redirect(url_for("home"))

@app.route("/toggle_theme", methods=["POST"])
def toggle_theme():
    session["theme"] = "light" if session.get("theme") == "dark" else "dark"
    return redirect(url_for("home"))

@app.route("/bookmark", methods=["POST"])
def bookmark():
    url = request.form.get("url")
    if "bookmarks" not in session:
        session["bookmarks"] = []
    if url and url not in session["bookmarks"]:
        session["bookmarks"].append(url)
    return redirect(url_for("home"))

@app.route("/browse")
def browse():
    url = request.args.get("url")
    if not url:
        return "URL is required", 400
    try:
        html = asyncio.run(render_with_playwright(url))
        return html
    except Exception as e:
        return f"Error fetching the URL: {str(e)}"

async def render_with_playwright(url):
    global USE_TOR
    user_agent = random.choice(USER_AGENTS)
    async with async_playwright() as p:
        browser_args = ["--no-sandbox"]
        if USE_TOR:
            browser_args.append("--proxy-server=socks5://127.0.0.1:9050")

        browser = await p.chromium.launch(headless=True, args=browser_args)
        context = await browser.new_context(
            user_agent=user_agent,
            java_script_enabled=True,
            ignore_https_errors=True,
            bypass_csp=True,
            permissions=[]
        )
        page = await context.new_page()

        # Remove known ad/cookie blocks (simple workaround)
        await page.route("**/*", lambda route, request: route.abort() if any(x in request.url for x in ["ads", "track", "analytics"]) else route.continue_())

        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)
        content = await page.content()
        await browser.close()
        return content

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)