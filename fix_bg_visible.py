import re

with open('index.html', 'r') as f:
    content = f.read()

# 1. INCREASE TASK WIDTH - make them fill more of the screen responsively
# Change from fixed 1000px to a percentage-based approach that adapts
old_tcard = r'''\.tcard {
    position: relative;
    width: 100%;
    max-width: 1000px;
    margin: 0 auto;'''

new_tcard = r'''\.tcard {
    position: relative;
    width: 100%;
    max-width: 95%;
    margin: 0 auto;'''

content = re.sub(old_tcard, new_tcard, content)

# Also update any other max-width: 920px or 1000px that apply to content containers
content = content.replace(
    '    max-width: 1000px;',
    '    max-width: 95%;'
)

# 2. MAKE BACKGROUND MORE VISIBLE - stronger gradients while maintaining ambient feel
# The key is to increase opacity enough to be visible but keep the blend mode correct
old_bg = r'''#bg-layer {
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  background: 
    radial-gradient\(circle at 25% 35%, rgba\(91, 156, 255, 0\.12\) 0%, transparent 50%\),
    radial-gradient\(circle at 75% 75%, rgba\(120, 194, 255, 0\.08\) 0%, transparent 55%\),
    radial-gradient\(circle at 50% 25%, rgba\(160, 140, 255, 0\.05\) 0%, transparent 45%\),
    radial-gradient\(ellipse 120% 80% at 50% 50%, rgba\(11, 15, 20, 0\.3\) 0%, rgba\(11, 15, 20, 0\.6\) 100%\),
    linear-gradient\(to bottom, rgba\(16, 22, 29, 0\.95\) 0%, rgba\(11, 15, 20, 1\) 50%, rgba\(11, 15, 20, 0\.95\) 100%\);
  background-blend-mode: screen, screen, screen, overlay, normal;
  background-color: #0B0F14;
  z-index: -2;
}'''

new_bg = '''#bg-layer {
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  background-color: #0B0F14;
  background: 
    /* Prominent primary light source - top-left */
    radial-gradient(ellipse 1000px 800px at 15% 20%, rgba(91, 156, 255, 0.25) 0%, transparent 60%),
    /* Strong secondary light - bottom-right */
    radial-gradient(ellipse 900px 900px at 85% 85%, rgba(120, 194, 255, 0.18) 0%, transparent 65%),
    /* Accent purple - top-right */
    radial-gradient(circle at 85% 10%, rgba(160, 140, 255, 0.12) 0%, transparent 50%),
    /* Deep atmosphere - edges darker */
    radial-gradient(ellipse 150% 100% at 50% 50%, transparent 30%, rgba(11, 15, 20, 0.7) 100%),
    /* Base layer */
    linear-gradient(135deg, #10161D 0%, #0B0F14 50%, #0F1319 100%);
  background-blend-mode: screen, screen, screen, overlay, normal;
  background-attachment: fixed;
  z-index: -2;
}'''

content = re.sub(old_bg, new_bg, content, flags=re.DOTALL)

# 3. ENSURE NOISE IS PRESENT AND VISIBLE
# Update noise opacity to 4% for more texture
content = content.replace(
    "opacity='0.03'",
    "opacity='0.04'"
)

with open('index.html', 'w') as f:
    f.write(content)

print('✓ Updated task width to 95% (responsive, fills screen)')
print('✓ Increased background gradients visibility')
print('✓ Enhanced gradient sizes and positions for clear ambient lighting')
print('✓ Increased noise layer to 4% opacity for texture')
