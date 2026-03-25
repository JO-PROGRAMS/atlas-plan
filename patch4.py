import re

with open("index.html", "r") as f:
    t = f.read()

# Fix tcard-inner height: 100% -> height: auto
t = t.replace(".tcard-inner {\n    padding: 24px;\n    display: flex;\n    flex-direction: column;\n    gap: 16px;\n    width: 100%;\n    height: 100%;", ".tcard-inner {\n    padding: 24px;\n    display: flex;\n    flex-direction: column;\n    gap: 16px;\n    width: 100%;\n    height: auto;")

# Fix topbar css properly. Find exactly `.topbar{`...`}` and make it background: transparent
t = re.sub(r'\.topbar\{[^}]+\}', r'.topbar{height:48px;padding:0 24px;display:flex;align-items:center;gap:10px;flex-shrink:0;background:transparent;position:relative;z-index:10;}', t)

# Fix noise div
t = re.sub(r'<div id="noise"></div>', '', t)

with open("index.html", "w") as f:
    f.write(t)
print("Finished!")
