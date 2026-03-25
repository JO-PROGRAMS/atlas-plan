import re

with open("index.html") as f: text = f.read()
text = re.sub(r"\.tcard\{height:180px;display:flex;flex-direction:column;justify-content:space-between;(?:height:180px;display:flex;flex-direction:column;justify-content:space-between;)+", ".tcard{display:flex;flex-direction:column;justify-content:space-between;min-height:180px;height:auto;", text)
text = re.sub(r'draggable=\\"true\\"\s*class=\\"tcard glass liquid-glass\\"', 'draggable=\\"true\\"', text)
text = re.sub(r'liquid-glass(?: liquid-glass)*(?: glass)*', 'liquid-glass', text)
text = text.replace('class="tcard glass ${pc}${newClass}"', 'class="tcard liquid-glass ${pc} ${newClass}"')

text = text.replace('width:100%;max-width:920px;margin:0 auto;', '')

with open("index.html", "w") as f: f.write(text)
print("done")
