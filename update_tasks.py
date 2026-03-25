import re

with open("index.html", "r") as f:
    html = f.read()

# 1. Update taskCardHTML to show more info and clean layout
old_func = r"function taskCardHTML\(t,i,newClass=''\)\{.*?return '';\s*\}\s*\}"
new_func = """function taskCardHTML(t,i,newClass=''){
  try{
    const pr=(t.priority||'').toLowerCase();
    const pc={'high':'phi','medium':'pm','low':'pl'}[pr]||'';
    const sc={'Done':'td','In progress':'tp','Planned':'tpl'}[t.status]||'tn';
    const pct={'High':'thi','Medium':'tme','Low':'tlo'}[t.priority]||'';
    const done=t.status==='Done';
    const due=t.due?fmtDue(t.due):'';
    const pinned=(t.priority==='High'||t.status==='In progress')?'1':'0';
    const animDelay=(i*.02);
    const idRaw=String(t.id||`task-${i}`);
    const idJs=escJsSingle(idRaw);
    const idAttr=escAttr(idRaw);
    const titleText=String(t.title||t.task_name||'Untitled task');
    const titleLower=titleText.toLowerCase();
    
    return `
      <div class="tcard liquid-glass ${pc} ${newClass}" data-id="${idAttr}" data-status="${escAttr((t.status||'').toLowerCase())}" data-title="${escAttr(titleLower)}" data-pinned="${pinned}" draggable="true" style="animation-delay:${animDelay}s">
        
        <div class="tc-head">
          <button class="tc-check ${done?'is-done':''}" aria-label="Toggle task done" onclick="toggleTaskDone('${idJs}',this)">${done?'✓':''}</button>
          
          <div class="tc-main">
            <div class="tc-title">${esc(titleText)}</div>
            ${t.summary ? `<div class="tc-sum">${esc(String(t.summary))}</div>` : ''}
            ${t.description ? `<div class="tc-desc">${esc(String(t.description))}</div>` : ''}
          </div>
          
          <div class="tc-actions">
            ${t.created_at ? `<div class="tc-meta">Created: ${new Date(t.created_at).toLocaleDateString()}</div>` : ''}
            <span class="tc-handle">⋮⋮</span>
          </div>
        </div>

        <div class="tc-foot">
          <div class="tc-tags">
            <span class="tag status-tag ${sc}">
               <span style="opacity:0.55;margin-right:4px;">Status:</span>${esc(String(t.status||'Not started'))}
            </span>
            ${t.priority?`<span class="tag ${pct}"><span style="opacity:0.55;margin-right:4px;">Priority:</span>${esc(String(t.priority))}</span>`:''}
            ${t.effort?`<span class="tag tef"><span style="opacity:0.55;margin-right:4px;">Effort:</span>${esc(String(t.effort))}</span>`:''}
            ${due?`<span class="tag tdu"><span style="opacity:0.55;margin-right:4px;">Due:</span>${esc(String(due))}</span>`:''}
            ${t.archived ? `<span class="tag tarch"><span style="opacity:0.55;">Archived</span></span>` : ''}
          </div>
        </div>
        
      </div>`;
  }catch(err){
    console.warn('Skipping malformed task row',t,err);
    return '';
  }
}"""
html = re.sub(old_func, new_func, html, flags=re.DOTALL)

# 2. Add the clean layout styles. Let's make sure we find the tcard declaration accurately.
css_fixes = """
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
    background: rgba(25, 33, 44, 0.45);
    backdrop-filter: blur(28px) saturate(120%);
    -webkit-backdrop-filter: blur(28px) saturate(120%);
    border: 1px solid rgba(255, 255, 255, 0.08); /* Increased for luminous feel */
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.07);
    padding: 24px;
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s ease, border-color 0.25s ease;
    /* REVERTED: overflow: hidden; isolation: isolate; to prevent clipping task elements like shadow/border/dropdowns */
}

.tcard:hover {
    border-color: rgba(255, 255, 255, 0.14);
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.12);
    transform: translateY(-2px);
    background: rgba(28, 38, 50, 0.5); /* Slight brighten on hover */
}

/* Redesigned Info Layout */
.tc-head {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 2px;
    min-width: 0;
    position: relative;
    z-index: 2;
}

.tc-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.tc-title {
    font-size: 17px;
    font-weight: 600;
    color: #F3F6FB;
    line-height: 1.4;
    letter-spacing: -0.2px;
    word-break: break-word; /* Essential for clipping fixes */
}

/* Summary vs Description Hierarchy */
.tc-sum, .tc-desc {
    font-size: 14px;
    color: #A4B1C5;
    line-height: 1.5;
    font-weight: 450;
    word-break: break-word;
    white-space: pre-wrap;
}
.tc-sum {
    opacity: 0.95;
    margin-top: 4px;
}
.tc-desc {
    color: #73849A;
    font-size: 13px;
    background: rgba(0, 0, 0, 0.15);
    padding: 12px 14px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.03);
    margin-top: 4px;
}

.tc-actions {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 12px;
    flex-shrink: 0;
    padding-top: 2px;
}

.tc-meta {
    font-size: 11px;
    color: #73849A;
    font-family: var(--font-mono), 'JetBrains Mono', monospace;
}

.tc-handle {
    font-size: 15px;
    letter-spacing: 1px;
    color: #52525b;
    cursor: grab;
    user-select: none;
    padding: 4px;
}
.tcard.dragging .tc-handle { cursor: grabbing; }

.tc-foot {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: flex-end;
    position: relative;
    z-index: 2;
    margin-top: 12px;
}

.tc-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

/* Premium Frosted Pills */
.tag {
    font-size: 12px;
    padding: 6px 12px;
    border-radius: 9px;
    font-family: 'Inter', -apple-system, sans-serif;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    border: 1px solid transparent;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    letter-spacing: 0.2px;
}

/* Soft tag coloring */
.tpl { background: rgba(255,255,255,0.05); color: #E5E7EB; border-color: rgba(255,255,255,0.06); }
.tn  { background: rgba(255,255,255,0.05); color: #E5E7EB; border-color: rgba(255,255,255,0.06); }
.td  { background: rgba(46, 219, 146, 0.1); color: #b6ffe0; border-color: rgba(46, 219, 146, 0.2); }
.tp  { background: rgba(91, 156, 255, 0.1); color: #9bc3ff; border-color: rgba(91, 156, 255, 0.2); }

.thi { background: rgba(240, 96, 96, 0.08); color: #f7b8b8; border-color: rgba(240, 96, 96, 0.18); }
.tme { background: rgba(245, 166, 35, 0.08); color: #f3d59e; border-color: rgba(245, 166, 35, 0.18); }
.tlo { background: rgba(91, 156, 255, 0.08); color: #9bc3ff; border-color: rgba(91, 156, 255, 0.15); }
.tef { background: rgba(255, 255, 255, 0.05); color: #A4B1C5; border-color: rgba(255, 255, 255, 0.05); }
.tdu { background: rgba(255, 255, 255, 0.05); color: #A4B1C5; border-color: rgba(255, 255, 255, 0.05); }
.tarch { background: rgba(0,0,0,0.4); color: #73849A; border-color: rgba(255,255,255,0.04); }

.tc-check {
    margin-top: 2px;
    width: 28px;
    height: 28px;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.12);
    background: rgba(20, 28, 36, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    color: transparent;
    font-size: 15px;
    transition: transform .2s ease, opacity .2s;
    flex-shrink: 0;
    cursor: pointer;
}
.tc-check:hover { transform: scale(1.08); border-color: rgba(255,255,255,0.25); }
.tc-check.is-done { color: #b6ffe0; opacity: 1; border-color: rgba(46, 219, 146, 0.4); background: rgba(46, 219, 146, 0.15); }

/* Ensure task controls have proper spacing */
.empty { max-width: 920px; margin: 0 auto; color: var(--t3); width: 100%; text-align: center; padding: 40px; }
"""

# Now clean up old blocks: We must remove old styles to prevent css cascades from duplicating and messing things up.
html = re.sub(r'\.tcard\s*\{(?:\s*position:\s*relative;\s*width:\s*100%;[\s\S]*?isolation:\s*isolate;\s*\})\s*', '', html)
html = re.sub(r'\.tcard:hover\s*\{[\s\S]*?transform:\s*translateY\(-2px\);\s*\}\s*', '', html)
html = re.sub(r'\.tc-title\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tc-head\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tc-main\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tc-check\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tc-check:hover\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tc-check\.is-done\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tc-handle\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tcard\.dragging\s*\.tc-handle\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tc-sum\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tc-foot\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tc-tags\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tag\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tpl\s*\{[^}]+\}\.tn\s*\{[^}]+\}', '', html)
html = re.sub(r'\.thi\s*\{[^}]+\}\.tme\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tlo\s*\{[^}]+\}\.tef\s*\{[^}]+\}', '', html)
html = re.sub(r'\.tdu\s*\{[^}]+\}', '', html)

# Insert fresh
html = html.replace("<style>", "<style>\n" + css_fixes)

with open("index.html", "w") as f:
    f.write(html)
