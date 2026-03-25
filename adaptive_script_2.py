import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Make tcard min-height larger
text = re.sub(r'min-height:\s*100px;', r'min-height: 120px;', text, count=1)
text = re.sub(r'min-height:\s*100px;', r'min-height: 120px;', text)
text = re.sub(r'min-height:100px;', r'min-height:120px;', text)

# Give inner wrapper auto height, ensure full box constraints and padding
text = re.sub(
    r'<div class="tcard-inner" style="[^"]*">',
    r'<div class="tcard-inner" style="display:flex; flex-direction:column; gap:22px; width:100%; box-sizing:border-box; height:100%; margin:0; padding:28px 32px; position:relative; overflow:visible; min-height:130px;">',
    text
)

# Top row wraps normally without being squashed
text = re.sub(
    r'<div class="tc-top-row" style="[^"]*">',
    r'<div class="tc-top-row" style="display:flex; flex-wrap:wrap; gap:10px; align-items:center; position:relative; z-index:5; width:100%; box-sizing:border-box; margin-bottom:0px; flex-shrink:0;">',
    text
)

# Mid row is fluid, stretching fully. No wrap on the row itself to keep checkbox + content lined up rigidly.
text = re.sub(
    r'<div class="tc-mid-row" style="[^"]*">',
    r'<div class="tc-mid-row" style="display:flex; gap:16px; align-items:flex-start; position:relative; z-index:3; width:100%; flex:1 1 auto; flex-wrap:nowrap;">',
    text
)

# Content col expands fully in the available mid-row space
text = re.sub(
    r'<div class="tc-content-col" style="[^"]*">',
    r'<div class="tc-content-col" style="flex:1 1 0%; min-width:0; display:flex; flex-direction:column; gap:6px;">',
    text
)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Done fixing dimensions in file.')
