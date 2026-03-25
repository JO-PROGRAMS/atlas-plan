import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Make sure we replace any existing styled tags with the highly flexible ones
text = re.sub(
    r'<div class="tcard-inner" style="[^"]*">',
    r'<div class="tcard-inner" style="display:flex; flex-direction:column; gap:18px; width:100%; box-sizing:border-box; height:auto; min-height:100%; margin:0; padding:28px 32px; position:relative; overflow:visible;">',
    text
)

text = re.sub(
    r'<div class="tc-top-row" style="[^"]*">',
    r'<div class="tc-top-row" style="display:flex; flex-wrap:wrap; gap:10px; align-items:center; position:relative; z-index:5; width:100%; box-sizing:border-box; margin-bottom:4px; flex-shrink:0;">',
    text
)

text = re.sub(
    r'<div class="tc-mid-row" style="[^"]*">',
    r'<div class="tc-mid-row" style="display:flex; gap:18px; align-items:flex-start; position:relative; z-index:3; width:100%; box-sizing:border-box; height:auto; flex-shrink:0;">',
    text
)

text = re.sub(
    r'<div class="tc-content-col" style="[^"]*">',
    r'<div class="tc-content-col" style="flex:1 1 auto; min-width:0; display:flex; flex-direction:column; gap:8px; width:100%; box-sizing:border-box;">',
    text
)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Done fixing dimensions.')
