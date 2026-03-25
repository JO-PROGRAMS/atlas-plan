import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

def replacer(cls, style_str):
    # Regex to replace `<div class="cls" style="...">` or `<div class="cls">`
    global text
    pattern = r'<div\s+class="' + cls + r'"(?:\s+style="[^"]*")?\s*>'
    replacement = f'<div class="{cls}" style="{style_str}">'
    text = re.sub(pattern, replacement, text)

# tcard-inner
replacer(
    "tcard-inner",
    "display:flex; flex-direction:column; gap:22px; width:100%; box-sizing:border-box; height:100%; margin:0; padding:28px 32px; position:relative; overflow:visible; min-height:130px;"
)

# tc-top-row
replacer(
    "tc-top-row",
    "display:flex; flex-wrap:wrap; gap:10px; align-items:center; position:relative; z-index:5; width:100%; box-sizing:border-box; margin-bottom:0px; flex-shrink:0;"
)

# tc-mid-row
replacer(
    "tc-mid-row",
    "display:flex; gap:16px; align-items:flex-start; position:relative; z-index:3; width:100%; flex:1 1 auto; flex-wrap:nowrap;"
)

# tc-content-col
replacer(
    "tc-content-col",
    "flex:1 1 0%; min-width:0; display:flex; flex-direction:column; gap:6px;"
)

# Also ensure max-width of tcard is correct if we need it wider. Let's make tcard perfectly adaptive but comfortable.
# User said "u reduced width". Maybe max-width was somehow smaller?
# Let's ensure max-width: 920px is respected and not squashed.
# tcard is max-width: 920px, let's keep it max-width: 920px, but ensure the inner flex is unconstrained inside it.

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Robust replacement done!')
