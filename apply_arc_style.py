import re

with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Update Typography to Inter and Colors to Aurora Midnight
new_css_vars = """  --font-ui: 'Inter', system-ui, -apple-system, sans-serif;
  --font-display: 'Inter', system-ui, -apple-system, sans-serif;
  --font-accent: 'Inter', system-ui, -apple-system, sans-serif;
  --bg: #0a0e17;
  --bg1: #101524;
  --bg2: #161d30;
  --t0: #ffffff;
  --t1: #e2e8f0;
  --t2: #94a3b8;
  --blue: #5b9cff;
  --blue2: #2a5fb8;
  --teal: #9bc3ff;"""

html = re.sub(r"--font-ui:[^;]*;.*?--bg2:[^;]*;", new_css_vars, html, flags=re.DOTALL)

# Let's ensure Google Fonts for Inter is included if not present
if "fonts.googleapis.com/css2?family=Inter" not in html:
    html = html.replace('<head>', '<head>\n<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">')

# 2. Refactor Layout 
html = re.sub(r'\.task-grid\{display:grid;grid-template-columns:1fr;.*?\n?\}', '.task-grid{display:flex;flex-direction:column;gap:12px;padding-top:8px;padding-bottom:30px;flex:1 1 auto;min-height:50px}', html)
html = re.sub(r'\.tcard\{[^\}]*\bmin-height:[^\}]*\}', '.tcard{width:100%;max-width:920px;margin:0 auto;display:flex;flex-direction:column;justify-content:flex-start;gap:12px;min-height:100px;height:auto;border-radius:24px;background:transparent !important;backdrop-filter:none !important;-webkit-backdrop-filter:none !important;box-shadow:none !important;border:1px solid rgba(255,255,255,0.08) !important;padding:24px;position:relative;cursor:grab;transition:transform 0.3s cubic-bezier(0.2,0.8,0.2,1);}', html, count=1)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Arc styling applied.")