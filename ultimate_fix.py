import re

with open("index.html", "r") as f:
    text = f.read()

# 1. Totally remove existing .tcard logic.
text = re.sub(r'\.tcard\s*\{[^}]+\}', '', text)
text = re.sub(r'\.tc-main\s*\{[^}]+\}', '', text)
text = re.sub(r'\.tc-head\s*\{[^}]+\}', '', text)
text = re.sub(r'\.tc-foot\s*\{[^}]+\}', '', text)
text = re.sub(r'\.tc-tags\s*\{[^}]+\}', '', text)

# Insert the premium, WebGL-respecting, zero-clipping layout.
new_css = """
/* The outer card is purely a bounding box for the WebGL liquid glass to track */
.tcard {
    position: relative;
    width: 100%;
    max-width: 920px;
    margin: 0 auto;
    min-height: 100px;
    height: auto;
    border-radius: 16px;
    
    /* MUST be transparent so WebGL Liquid Glass beneath it shows through!!! */
    background: transparent !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    box-shadow: none !important;
    
    /* Elegant outer rim light that syncs with WebGL refraction */
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    
    cursor: grab;
    transition: transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.tcard:hover {
    transform: translateY(-2px);
    border-color: rgba(255, 255, 255, 0.15) !important;
}

/* Inner content wrapper controls actual padding and prevents clipping */
.tcard-inner {
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    width: 100%;
    height: 100%;
    position: relative;
    z-index: 2;
}

/* Redesigned Info Layout - Beautiful Row Ordering */
.tc-top-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
    position: relative;
    z-index: 3;
}

.tc-mid-row {
    display: flex;
    gap: 16px;
    align-items: flex-start;
}

.tc-checkbox-col {
    margin-top: 2px;
}

.tc-content-col {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.tc-actions-col {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 8px;
}

.tc-title {
    font-size: 18px;
    font-weight: 600;
    color: #F3F6FB;
    line-height: 1.4;
    letter-spacing: -0.2px;
    word-break: break-word;
    text-shadow: 0px 2px 4px rgba(0,0,0,0.5); /* Shadow text because bg is glass */
}

/* Rich detail styling */
.tc-desc {
    font-size: 14px;
    color: #A4B1C5;
    line-height: 1.5;
    background: rgba(0, 0, 0, 0.15); /* Slightly darker inner inset */
    padding: 12px 16px;
    border-radius: 12px;
    border: 1px inset rgba(255,255,255,0.03);
    margin-top: 4px;
    white-space: pre-wrap;
    word-break: break-word;
}

.tc-meta {
    font-size: 11px;
    color: rgba(255,255,255,0.4);
    font-family: var(--font-mono), 'JetBrains Mono', monospace;
}

.tc-handle {
    font-size: 16px;
    color: rgba(255,255,255,0.3);
    cursor: grab;
    padding: 4px;
}

.tc-check {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.15);
    background: rgba(0, 0, 0, 0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    color: transparent;
    font-size: 15px;
    transition: transform .2s ease, opacity .2s, border-color .2s;
    cursor: pointer;
}
.tc-check:hover { transform: scale(1.08); border-color: rgba(255,255,255,0.3); }
.tc-check.is-done { color: #b6ffe0; opacity: 1; border-color: rgba(46, 219, 146, 0.4); background: rgba(46, 219, 146, 0.15); }

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

/* Luminous transparent colors */
.tpl { background: rgba(255,255,255,0.05); color: #E5E7EB; border-color: rgba(255,255,255,0.06); }
.tn  { background: rgba(255,255,255,0.05); color: #E5E7EB; border-color: rgba(255,255,255,0.06); }
.td  { background: rgba(46, 219, 146, 0.12); color: #b6ffe0; border-color: rgba(46, 219, 146, 0.2); }
.tp  { background: rgba(91, 156, 255, 0.12); color: #9bc3ff; border-color: rgba(91, 156, 255, 0.2); }

.thi { background: rgba(240, 96, 96, 0.1); color: #f7b8b8; border-color: rgba(240, 96, 96, 0.15); }
.tme { background: rgba(245, 166, 35, 0.1); color: #f3d59e; border-color: rgba(245, 166, 35, 0.15); }
.tlo { background: rgba(91, 156, 255, 0.1); color: #9bc3ff; border-color: rgba(91, 156, 255, 0.12); }
.tef { background: rgba(255, 255, 255, 0.05); color: #A4B1C5; border-color: rgba(255, 255, 255, 0.05); }
.tdu { background: rgba(255, 255, 255, 0.05); color: #A4B1C5; border-color: rgba(255, 255, 255, 0.05); }
"""
text = text.replace("<style>", "<style>\n" + new_css)

# Remove the old taskCardHTML definition fully.
# (We handle formatting correctly so there aren't duplicated JS blocks).
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
    
    // Explicit condition so we don't render 'No content' strings
    const hasSummaryString = t.summary && String(t.summary).toLowerCase() !== 'no content' && String(t.summary).trim() !== '';
    const summaryHtml = hasSummaryString ? `<div class="tc-desc">${esc(String(t.summary))}</div>` : '';
    
    return `
      <div class="tcard liquid-glass ${pc} ${newClass}" data-id="${idAttr}" data-status="${escAttr((t.status||'').toLowerCase())}" data-title="${escAttr(titleLower)}" data-pinned="${pinned}" draggable="true" style="animation-delay:${animDelay}s">
        
        <div class="tcard-inner">
            <!-- 1. Beautiful floating tags row at the true top inside the container -->
            <div class="tc-top-row">
                <span class="tag status-tag ${sc}">
                   <span style="opacity:0.55;margin-right:4px;">Status:</span>${esc(String(t.status||'Not started'))}
                </span>
                ${t.priority?`<span class="tag ${pct}"><span style="opacity:0.55;margin-right:4px;">Priority:</span>${esc(String(t.priority))}</span>`:''}
                ${t.effort?`<span class="tag tef"><span style="opacity:0.55;margin-right:4px;">Effort:</span>${esc(String(t.effort))}</span>`:''}
                ${due?`<span class="tag tdu"><span style="opacity:0.55;margin-right:4px;">Due:</span>${esc(String(due))}</span>`:''}
            </div>

            <!-- 2. Mid row containing checkbox, title, summary -->
            <div class="tc-mid-row">
                <div class="tc-checkbox-col">
                    <button class="tc-check ${done?'is-done':''}" aria-label="Toggle task done" onclick="toggleTaskDone('${idJs}',this)">${done?'✓':''}</button>
                </div>
                
                <div class="tc-content-col">
                    <div class="tc-title">${esc(titleText)}</div>
                    ${summaryHtml}
                </div>
                
                <div class="tc-actions-col">
                    <span class="tc-handle">⋮⋮</span>
                    ${t.created_at ? `<div class="tc-meta">${new Date(t.created_at).toLocaleDateString()}</div>` : ''}
                </div>
            </div>
        </div>
        
      </div>`;
  }catch(err){
    console.warn('Skipping malformed task row',t,err);
    return '';
  }
}"""
text = re.sub(old_func, new_func, text, flags=re.DOTALL)

with open("index.html", "w") as f:
    f.write(text)

