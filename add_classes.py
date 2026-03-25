with open("index.html", "r") as f:
    text = f.read()
text = text.replace('liquid-btn', 'liquid-btn liquid-glass')
with open("index.html", "w") as f:
    f.write(text)
