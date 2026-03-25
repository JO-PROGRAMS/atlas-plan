import re

with open("index.html", "r") as f:
    text = f.read()

# Remove any old .tcard inline definitions that are heavily compressed
text = re.sub(r'\.tcard\{[^\}]+\}', '', text)
text = re.sub(r'^\s*\.tcard::before\s*\{.*?\}$', '', text, flags=re.MULTILINE|re.DOTALL)
text = re.sub(r'^\s*\.tcard::after\s*\{.*?\}$', '', text, flags=re.MULTILINE|re.DOTALL)
text = re.sub(r'\.tcard\s*\{\s*background:\s*transparent\s*!important;.*?\}', '', text, flags=re.DOTALL)

with open("index.html", "w") as f:
    f.write(text)

