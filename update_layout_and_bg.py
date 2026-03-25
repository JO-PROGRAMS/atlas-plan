import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Increase max-width from 920px to 1000px for featured items (task cards)
text = text.replace('    max-width: 920px;', '    max-width: 1000px;')

# 2. Update taskCardHTML to move tags below title
# Current structure: tc-top-row (tags), then tc-mid-row (checkbox+title+summary)
# New structure: tc-mid-row (checkbox+title+summary), then tc-tags-row (tags)

old_taskcard_html = r'''    return `
      <div class="tcard liquid-glass ${pc} ${newClass}" data-id="${idAttr}" data-status="${escAttr((t.status||'').toLowerCase())}" data-title="${escAttr(titleLower)}" data-pinned="${pinned}" draggable="true" style="animation-delay:${animDelay}s">
        
        <div class="tcard-inner" style="display:flex; flex-direction:column; gap:22px; width:100%; box-sizing:border-box; height:100%; margin:0; padding:28px 32px; position:relative; overflow:visible; min-height:130px;">
            <!-- 1. Beautiful floating tags row at the true top inside the container -->
            <div class="tc-top-row" style="display:flex; flex-wrap:wrap; gap:10px; align-items:center; position:relative; z-index:5; width:100%; box-sizing:border-box; margin-bottom:0px; flex-shrink:0;">
                <span class="tag status-tag ${sc}">
                   <span style="opacity:0.55;margin-right:4px;">Status:</span>${esc(String(t.status||'Not started'))}
                </span>
                ${t.priority?`<span class="tag ${pct}"><span style="opacity:0.55;margin-right:4px;">Priority:</span>${esc(String(t.priority))}</span>`:''}
                ${t.effort?`<span class="tag tef"><span style="opacity:0.55;margin-right:4px;">Effort:</span>${esc(String(t.effort))}</span>`:''}
                ${due?`<span class="tag tdu"><span style="opacity:0.55;margin-right:4px;">Due:</span>${esc(String(due))}</span>`:''}
            </div>

            <!-- 2. Mid row containing checkbox, title, summary -->
            <div class="tc-mid-row" style="display:flex; gap:16px; align-items:flex-start; position:relative; z-index:3; width:100%; flex:1 1 auto; flex-wrap:nowrap;">
                <div class="tc-checkbox-col" style="flex-shrink:0;">
                    <button class="tc-check ${done?'is-done':''}" aria-label="Toggle task done" onclick="toggleTaskDone('${idJs}',this)">${done?'✓':''}</button>
                </div>
                
                <div class="tc-content-col" style="flex:1 1 0%; min-width:0; display:flex; flex-direction:column; gap:6px;">
                    <div class="tc-title">${esc(titleText)}</div>
                    ${summaryHtml}
                </div>
                
                <div class="tc-actions-col" style="flex-shrink:0; display:flex; flex-direction:column; align-items:flex-end; gap:8px;">
                    <span class="tc-handle">⋮⋮</span>
                    ${t.created_at ? `<div class="tc-meta">${new Date(t.created_at).toLocaleDateString()}</div>` : ''}
                </div>
            </div>
        </div>
        
      </div>`;'''

new_taskcard_html = r'''    return `
      <div class="tcard liquid-glass ${pc} ${newClass}" data-id="${idAttr}" data-status="${escAttr((t.status||'').toLowerCase())}" data-title="${escAttr(titleLower)}" data-pinned="${pinned}" draggable="true" style="animation-delay:${animDelay}s">
        
        <div class="tcard-inner" style="display:flex; flex-direction:column; gap:18px; width:100%; box-sizing:border-box; height:100%; margin:0; padding:28px 32px; position:relative; overflow:visible; min-height:130px;">
            <!-- 1. Main row containing checkbox, title, and actions -->
            <div class="tc-mid-row" style="display:flex; gap:16px; align-items:flex-start; position:relative; z-index:3; width:100%; flex-wrap:nowrap;">
                <div class="tc-checkbox-col" style="flex-shrink:0;">
                    <button class="tc-check ${done?'is-done':''}" aria-label="Toggle task done" onclick="toggleTaskDone('${idJs}',this)">${done?'✓':''}</button>
                </div>
                
                <div class="tc-content-col" style="flex:1 1 0%; min-width:0; display:flex; flex-direction:column; gap:12px;">
                    <div class="tc-title">${esc(titleText)}</div>
                    
                    <!-- 2. Tags row below title -->
                    <div class="tc-tags-row" style="display:flex; flex-wrap:wrap; gap:8px; align-items:center; position:relative; z-index:4;">
                        <span class="tag status-tag ${sc}">
                           <span style="opacity:0.55;margin-right:4px;">Status:</span>${esc(String(t.status||'Not started'))}
                        </span>
                        ${t.priority?`<span class="tag ${pct}"><span style="opacity:0.55;margin-right:4px;">Priority:</span>${esc(String(t.priority))}</span>`:''}
                        ${t.effort?`<span class="tag tef"><span style="opacity:0.55;margin-right:4px;">Effort:</span>${esc(String(t.effort))}</span>`:''}
                        ${due?`<span class="tag tdu"><span style="opacity:0.55;margin-right:4px;">Due:</span>${esc(String(due))}</span>`:''}
                    </div>
                    
                    ${summaryHtml}
                </div>
                
                <div class="tc-actions-col" style="flex-shrink:0; display:flex; flex-direction:column; align-items:flex-end; gap:8px;">
                    <span class="tc-handle">⋮⋮</span>
                    ${t.created_at ? `<div class="tc-meta">${new Date(t.created_at).toLocaleDateString()}</div>` : ''}
                </div>
            </div>
        </div>
        
      </div>`;'''

text = text.replace(old_taskcard_html, new_taskcard_html)

# 3. Update the background with the layered gradient system
# Find and replace the #bg-layer CSS

old_bg_layer = r'''#bg-layer {
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  background: 
    radial-gradient(circle at 20% 30%, rgba(100, 150, 255, 0.25) 0%, transparent 60%),
    radial-gradient(circle at 80% 80%, rgba(235, 100, 160, 0.2) 0%, transparent 60%),
    radial-gradient(circle at 80% 10%, rgba(50, 200, 200, 0.25) 0%, transparent 50%),
    linear-gradient(175deg, rgba(28, 40, 65, 0.7) 0%, rgba(45, 30, 61, 0.8) 40%, rgba(22, 35, 58, 0.85) 70%, rgba(15, 20, 35, 0.95) 100%),
    url('assets/default.avif') center/cover no-repeat;
  background-blend-mode: screen, screen, screen, normal, normal;
  z-index: -2;
}'''

new_bg_layer = r'''#bg-layer {
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  background: 
    radial-gradient(circle at 25% 35%, rgba(91, 156, 255, 0.12) 0%, transparent 50%),
    radial-gradient(circle at 75% 75%, rgba(120, 194, 255, 0.08) 0%, transparent 55%),
    radial-gradient(circle at 50% 25%, rgba(160, 140, 255, 0.05) 0%, transparent 45%),
    radial-gradient(ellipse 120% 80% at 50% 50%, rgba(11, 15, 20, 0.3) 0%, rgba(11, 15, 20, 0.6) 100%),
    linear-gradient(to bottom, rgba(16, 22, 29, 0.95) 0%, rgba(11, 15, 20, 1) 50%, rgba(11, 15, 20, 0.95) 100%),
    #0B0F14;
  background-blend-mode: screen, screen, screen, overlay, normal, normal;
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

text = text.replace(old_bg_layer, new_bg_layer)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('✓ Updated card width to 1000px')
print('✓ Restructured layout to move tags below title')
print('✓ Updated background with layered gradient system')
