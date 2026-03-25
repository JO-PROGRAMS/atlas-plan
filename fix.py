import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'<div class="tcard-inner">', r'<div class="tcard-inner" style="display:flex; flex-direction:column; gap:16px; min-height:min-content; margin:0; padding:24px; position:relative; overflow:visible;">', text)

text = re.sub(r'<div class="tc-top-row">', r'<div class="tc-top-row" style="display:flex; flex-wrap:wrap; gap:8px; align-items:center; position:relative; z-index:5; min-height:24px; margin-bottom:8px; flex-shrink:0;">', text)

text = re.sub(r'<div class="tc-mid-row">', r'<div class="tc-mid-row" style="display:flex; gap:16px; align-items:flex-start; position:relative; z-index:3; min-height:30px; flex-shrink:0;">', text)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('done')
