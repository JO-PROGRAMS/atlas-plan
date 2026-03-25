import re

with open("index.html", "r") as f:
    html = f.read()

# Typography and gradients
html = re.sub(r"font-family:var\(--font-ui\),.*?;", r"font-family:var(--font-ui),-apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif;", html)

css_vars = """
  --font-ui: 'Inter', system-ui, -apple-system, sans-serif;
  --font-display: 'Inter', system-ui, -apple-system, sans-serif;
  --font-accent: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', monospace;
  --bg:    #000000;
  --bg1:   #0a0a0a;
  --bg2:   #111111;
  --bg3:   #1a1a1a;
  --bg4:   #222222;
  --rim:   rgba(255,255,255,0.06);
  --rim2:  rgba(255,255,255,0.1);
  --rim3:  rgba(255,255,255,0.15);
  --t0:    #ffffff;
  --t1:    #ededed;
  --t2:    #a1a1aa;
  --t3:    #71717a;
  --t4:    #52525b;
  --blue:  #5e6ad2;
  --blue2: #3f48a8;
  --teal:  #5ed2c3;
"""
html = re.sub(r"--font-ui:.*?--teal:\s*#[a-zA-Z0-9]+;", css_vars.strip(), html, flags=re.DOTALL)

# Background gradient (linear style)
html = re.sub(r"
with oprad    html = f.read()

# Typographydi
# Typography and a 0html = re.sub(r"font-fami
#
css_vars = """
  --font-ui: 'Inter', system-ui, -apple-system, sans-seri,20,0.5) !important;
  backdrop-filter: blur(24px) saturate(1.5) !important;
    --font-ui: ro  --font-display: 'Inter', system-ui, -apple-system, sans-px  --font-accent: 'In255,0.08) !important;
  box-shadow: 0 8px 32p  --font-mono: 'JetBrains Mono', 'SF Mono', monospace;
  --bg:tm  --bg:    #000000;
  --bg1:   #0a0a0a;
  --bg2:   #1--  --bg1:   #0a0a0ava  --bg2:   #111111*?  --bg3:   #1a1a, gl  --bg4:   #222, htm  --rim:   rgba(25)
  --rim2:  rgba(255,255,255,0.1); r  --rim3:  rgba(255,255,255,0.15\.  --t0:    #ffffff;
  --t1:    #e.2  --t1:    #ededed s  --t2:    #a1a1aari  --t3:    #71717(r"  --t4:    #52525bgr  --blue:  #5e6ad2\(  --blue2: #3f48a8ba  -55,255,255,\.72\)"""
html = re.sub(,2ht,0
# Bac, r"background:linear-gradient(90deg,rgba(255,255,255,0) 0%,rgba(255,255,255,1) 50%,rgba(255html = re.sub(r"
with oprad    htmlenwith oprad    h"w
) as f:
    f.write(html)
