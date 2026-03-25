import re

with open("index.html", "r") as f:
    content = f.read()

# Update .tcard glass styles
new_tcard = r'''
.tcard {
    position: relative;
    padding: 20px 24px;
    border-radius: 16px;
    background: rgba(20, 28, 36, 0.5);
    backdrop-filter: blur(24px) saturate(130%);
    -webkit-backdrop-filter: blur(24px) saturate(130%);
    border: 1px solid rgba(255, 255, 255, 0.06);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.04);
    display: flex;
    flex-direction: column;
    gap: 12px;
    overflow: hidden;
    isolation: isolate;
    transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease, background 0.2s ease;
}
'''

content = re.sub(r'\.tcard\s*\{.*?(?=\.tcard\s*::before|\.tcard\s*::after|:hover|\})', new_tcard, content, flags=re.DOTALL)

with open("index.html", "w") as f:
    f.write(content)
