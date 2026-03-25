with open("index.html", "r") as f:
    text = f.read()

import re
old_grad = "linear-gradient(175deg, #1c2841 0%, #2d1e3d 40%, #16233a 70%, #0f1423 100%)"
new_grad = "linear-gradient(175deg, rgba(28, 40, 65, 0.7) 0%, rgba(45, 30, 61, 0.8) 40%, rgba(22, 35, 58, 0.85) 70%, rgba(15, 20, 35, 0.95) 100%)"

text = text.replace(old_grad, new_grad)

with open("index.html", "w") as f:
    f.write(text)
print("Opacity fixed!")
