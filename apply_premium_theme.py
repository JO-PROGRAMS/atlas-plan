import re

with open("index.html", "r") as f:
    content = f.read()

# 1. Update css root variables for the dark luminous theme
theme_vars = {
    '--bg': '#0B0F14',
    '--bg-2': '#10161D',
    '--bg-3': '#141C24',
    '--t0': '#F3F6FB',
    '--t1': '#A4B1C5',
    '--t2': '#73849A',
    '--blue': '#5B9CFF',
    '--pane': 'rgba(20, 28, 36, 0.5)',
    '--border': 'rgba(255, 255, 255, 0.06)'
}

for k, v in theme_vars.items():
    content = re.sub(rf'{k}:\s*[^;]+;', f'{k}: {v};', content)

# 2. Add soft lighting gradient background to body and setup font overrides
new_body_css = '''
body {
    background-color: var(--bg);
    background-image: 
        radial-gradient(circle at 15% 50%, rgba(91, 156, 255, 0.04) 0%, transparent 50%),
        radial-gradient(circle at 85% 30%, rgba(164, 177, 197, 0.03) 0%, transparent 50%);
    background-attachment: fixed;
    color: var(--t1);
    font-family: 'Inter', -apple-system, sans-serif;
    font-weight: 500;
}
h1, h2, h3, h4, h5, h6 {
    font-weight: 600;
    color: var(--t0);
}
'''

content = re.sub(r'body\s*\{[^}]*\}', new_body_css, content, count=1)

# 3. Update the .tcard to have frosted glass, depth, edge shimmer, refined spacing
new_tcard_css = '''
.tcard {
    position: relative;
    width: 100%;
    max-width: 920px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    gap: 12px;
    min-height: 100px;
    height: auto;
    border-radius: 16px;
    
    /* Frosted glass */
    background: rgba(20, 28, 36, 0.5);
    backdrop-filter: blur(24px) saturate(130%);
    -webkit-backdrop-filter: blur(24px) saturate(130%);
    border: 1px solid var(--border);
    
    /* Subtle depth */
    box-shadow: 
        0 8px 32px rgba(0, 0, 0, 0.15), 
        inset 0 1px 0 rgba(255, 255, 255, 0.08); /* top highlight */
        
    padding: 20px 24px;
    cursor: grab;
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), 
                box-shadow 0.25s ease, 
                border-color 0.25s ease;
    
    /* Zero layout clipping fixes */
    overflow: hidden;
    isolation: isolate;
}

/* Subtle edge shimmer on hover */
.tcard:hover {
    border-color: rgba(255, 255, 255, 0.12);
    box-shadow: 
        0 12px 48px rgba(0, 0, 0, 0.25), 
        inset 0 1px 0 rgba(255, 255, 255, 0.12);
    transform: translateY(-2px);
}
'''

# Replace the first massive .tcard rule
content = re.sub(r'\.tcard\s*\{[^}]*\}', new_tcard_css, content, count=1)

# Delete existing problematic !important overrides for .tcard
content = re.sub(r'\.tcard\s*\{\s*background:\s*transparent\s*!important;.*?\}', '', content, flags=re.DOTALL)

with open("index.html", "w") as f:
    f.write(content)
