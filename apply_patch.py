import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Background fix
html = re.sub(
    r"background:\s*url\('https://images\.unsplash\.com/[^']+'\)\s*center/cover\s*no-repeat;?",
    "background: linear-gradient(175deg, hsla(232, 78%, 24%, 1) 0%, hsla(210, 20%, 6%, 1) 68%);",
    html
)

# 2. Button removals
html = html.replace('<button class="gbtn" onclick="loadTasks()" style="margin-left:auto">Refresh</button><button class="gbtn" onclick="exportJSON()">Export JSON</button>', '')
html = re.sub(r'<div class="tc-actions">.*?</div>', '', html, flags=re.DOTALL)
html = re.sub(r'\.tc-actions\{.*?\}', '', html)
html = re.sub(r'\.tc-actions \.tc-btn\{.*?\}', '', html)

# 3. Tcard clipping issues fix
html = re.sub(r'\.tc-sum\{.*?\}', '.tc-sum{font-size:14px;color:rgba(255,255,255,.8);line-height:1.6;margin-top:8px;margin-bottom:12px;font-weight:400;width:100%;white-space:pre-wrap;display:block;}', html)

html = re.sub(
    r'\.tcard\{[^\}]*\bmin-height:180px;height:auto;[^\}]*\}',
    '.tcard{width:100%;max-width:920px;margin:0 auto;display:flex;flex-direction:column;justify-content:flex-start;gap:12px;min-height:120px;height:auto;border-radius:24px;background:rgba(255,255,255,0.02);backdrop-filter:blur(32px) saturate(1.2);-webkit-backdrop-filter:blur(32px) saturate(1.2);border:1px solid rgba(255,255,255,0.1);padding:24px;position:relative;cursor:grab;transition:transform 0.3s cubic-bezier(0.2,0.8,0.2,1),box-shadow 0.3s cubic-bezier(0.2,0.8,0.2,1);box-shadow:inset 0 1px 0 rgba(255,255,255,0.15),inset 0 0 12px rgba(255,255,255,0.05),0 12px 32px rgba(0,0,0,0.3);}',
    html,
    count=1,
    flags=re.DOTALL
)

html = re.sub(r'\.tgrid\{[^\}]*\bdisplay:grid;grid-template-columns:repeat[^\}]*\}', '.tgrid{flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;padding:18px 20px 28px;display:flex;flex-direction:column;gap:12px;width:100%;align-items:center;position:relative;}', html)
html = re.sub(r'\.task-grid\{[^\}]*\bdisplay:grid;grid-template-columns:repeat[^\}]*\}', '.task-grid{display:flex;flex-direction:column;gap:12px;width:100%;max-width:920px;margin:0 auto;padding-top:8px;padding-bottom:30px;flex:1 1 auto;min-height:50px}', html)

# 4. Drag & Drop FLIP logic
old_dragover = """  container.addEventListener('dragover',e=>{
    e.preventDefault();
    const dragging=container.querySelector('.dragging');
    if(!dragging) return;
    updateDragFx(dragging,e.clientX,e.clientY);
    const afterEl=dragAfterElement(e.clientY);
    if(afterEl==null){container.appendChild(dragging);return;}
    container.insertBefore(dragging,afterEl);
  });"""

new_dragover = """  container.addEventListener('dragover',e=>{
    e.preventDefault();
    const dragging=container.querySelector('.dragging');
    if(!dragging) return;
    updateDragFx(dragging,e.clientX,e.clientY);
    const afterEl=dragAfterElement(e.clientY);
    
    // Smooth FLIP animation sequence
    const currentNext = dragging.nextElementSibling;
    if (afterEl === currentNext) return;

    // First
    const cards = [...container.querySelectorAll('.tcard:not(.dragging)')];
    const firstRects = new Map();
    cards.forEach(c => firstRects.set(c, c.getBoundingClientRect()));

    // Insert DOM change
    if(afterEl==null){container.appendChild(dragging);}
    else {container.insertBefore(dragging,afterEl);}

    // Last & Invert & Play
    cards.forEach(c => {
      const first = firstRects.get(c);
      if(!first) return;
      
      const oldTrans = c.style.transform;
      const oldTrs = c.style.transition;
      
      c.style.transition = 'none';
      c.style.transform = 'none';
      const last = c.getBoundingClientRect();
      
      const dx = first.left - last.left;
      const dy = first.top - last.top;
      
      if(dx !== 0 || dy !== 0) {
          c.style.transform = `translate(${dx}px, ${dy}px)`;
          c.getBoundingClientRect(); // reflow
          c.style.transition = 'transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1)';
          c.style.transform = 'none';
          setTimeout(() => {
              if(c.style.transition.includes('transform 0.4s')) {
                  c.style.transition = oldTrs;
                  c.style.transform = oldTrans || '';
              }
          }, 400);
      } else {
          c.style.transition = oldTrs;
          c.style.transform = oldTrans || '';
      }
    });
  });"""

html = html.replace(old_dragover, new_dragover)

# 5. Increase Refraction contrast
html = html.replace(
    'background:conic-gradient(from calc((var(--drag-x) + var(--drag-y)) * 180deg),rgba(255,108,130,.56),rgba(255,191,105,.56),rgba(253,242,120,.5),rgba(130,246,189,.52),rgba(125,211,252,.56),rgba(167,139,250,.58),rgba(244,114,182,.56),rgba(255,108,130,.56));',
    'background:conic-gradient(from calc((var(--drag-x) + var(--drag-y)) * 180deg),rgba(255,108,130,.86),rgba(255,191,105,.86),rgba(253,242,120,.8),rgba(130,246,189,.82),rgba(125,211,252,.86),rgba(167,139,250,.88),rgba(244,114,182,.86),rgba(255,108,130,.86));'
)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Patch applied successfully")