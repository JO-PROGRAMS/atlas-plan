import re

with open("index.html", "r") as f:
    text = f.read()

new_bg_layer_css = """#bg-layer {
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  background: 
    radial-gradient(circle at 20% 30%, rgba(100, 150, 255, 0.25) 0%, transparent 60%),
    radial-gradient(circle at 80% 80%, rgba(235, 100, 160, 0.2) 0%, transparent 60%),
    radial-gradient(circle at 80% 10%, rgba(50, 200, 200, 0.25) 0%, transparent 50%),
    linear-gradient(175deg, #1c2841 0%, #2d1e3d 40%, #16233a 70%, #0f1423 100%), 
    url('assets/default.avif') center/cover no-repeat;
  background-blend-mode: screen, screen, screen, normal, normal;
  z-index: -2;
}"""

# simple regex replace
text = re.sub(r'#bg-layer\s*\{[^}]+\}', new_bg_layer_css, text)

# update main HTML body background to just fallback so it doesn't conflict with bg-layer
text = re.sub(r'html,body\{height:100%;\s*background: [^;]+;\s*', r'html,body{height:100%;background:#0f1423;\n', text)

with open("index.html", "w") as f:
    f.write(text)
print("CSS patched!")