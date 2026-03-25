import re

with open("index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Protect checkbox-col from squashing
text = re.sub(
    r'<div class="tc-checkbox-col">',
    r'<div class="tc-checkbox-col" style="flex-shrink:0;">',
    text
)

# Protect actions-col from squashing
text = re.sub(
    r'<div class="tc-actions-col">',
    r'<div class="tc-actions-col" style="flex-shrink:0; display:flex; flex-direction:column; align-items:flex-end; gap:8px;">',
    text
)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(text)

