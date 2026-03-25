import re

with open('index.html', 'r') as f:
    content = f.read()

# Replace the #bg-layer block using a flexible regex
pattern = r'#bg-layer\s*\{\s*position:\s*fixed;[^}]+\}'

replacement = '''#bg-layer {
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  background: 
    radial-gradient(circle at 25% 35%, rgba(91, 156, 255, 0.12) 0%, transparent 50%),
    radial-gradient(circle at 75% 75%, rgba(120, 194, 255, 0.08) 0%, transparent 55%),
    radial-gradient(circle at 50% 25%, rgba(160, 140, 255, 0.05) 0%, transparent 45%),
    radial-gradient(ellipse 120% 80% at 50% 50%, rgba(11, 15, 20, 0.3) 0%, rgba(11, 15, 20, 0.6) 100%),
    linear-gradient(to bottom, rgba(16, 22, 29, 0.95) 0%, rgba(11, 15, 20, 1) 50%, rgba(11, 15, 20, 0.95) 100%);
  background-blend-mode: screen, screen, screen, overlay, normal;
  background-color: #0B0F14;
  z-index: -2;
}

#bg-layer::before {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.03'/%3E%3C/svg%3E");
  background-size: 200px 200px;
  pointer-events: none;
  z-index: 1;
}'''

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('index.html', 'w') as f:
    f.write(content)

print('✓ Background replaced with new gradient system')
