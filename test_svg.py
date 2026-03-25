import re

with open("index.html") as f:
    text = f.read()

# Strip out webgl stuff
text = re.sub(r'// ═══════════════════════════════════════════════════════\n//   WEBGL LIQUID GLASS\n// ═══════════════════════════════════════════════════════.*?</script>', '</script>', text, flags=re.DOTALL)
text = text.replace('<canvas id="webgl-glass"></canvas>', '')

# Update CSS for .tcard
old_glass_css = r"""\.liquid-glass \{ background: rgba\(255,255,255,0\.01\) !important; backdrop-filter: none !important; -webkit-backdrop-filter: none !important; box-shadow: 0 10px 30px rgba\(0,0,0,0\.5\); \}                                                           \.liquid-glass::before, \.liquid-glass::after \{ display: none !important; \}.*?\}"""
text = re.sub(r'\.liquid-glass \{ backimport re

with open("indeag
with opALL    text = f.read()

# Stripss
# Strip out webgxt)
text = re.sub(r'// ═idtext = text.replace('<canvas id="webgl-glass"></canvas>', '')

# Update CSS for .tcard
old_glass_css = r"""\.liquid-glass \{ background: rgba\(255,255,255,0\.01\) !important; backdrop-filter: none !important; -webkit-backdrop-filter: none !important; box-shadow: 0 10px 30px rgba\(0,0,0,0\.5\); \}                                                           \.liquid-glass::before, \.liquid-glass::after \{ display: none !importannt
# Update CSS for .tcard
old_glass_css = r"""\.liquid-glass  + old_glass_css = r"""\.catext = re.sub(r'\.liquid-glass \{ backimport re

with open("indeag
with opALL    text = f.read()

# Stripss
# Strip out webgxt)
text = re.sub(r'// ═idtext = text.replace('<canvas id="webgl-glass"></canvas>', '')

# Update CSS for .tcard
old_glass_css = r"""\.liquid-glass \{ background: rgba\(255,255,255,0\.01\) !important; backdrop-filter: none !impte
with open("indeag
with opALL    text = f.readKENwith opALL    te??# Stripss
# Strip out webgx ════text = re.sub(r'//??
# Update CSS for .tcard
old_glass_css = r"""\.liquid-glass \{ background: rgba\int("doold)
