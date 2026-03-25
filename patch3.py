import re

with open("index.html", "r") as f:
    t = f.read()

old_toggle = """async function toggleTaskDone(id,btn){
  const card=btn.closest('.tcard');
  const current=(card?.dataset.status||'').toLowerCase();
  if(current==='done') return markInProg(id,card.querySelector('.tc-btn:not(.done)'));
  return markDone(id,card.querySelector('.tc-btn.done'));
}
async function markDone(id,btn){
  const card=btn.closest('.tcard');
  btn.disabled=true;btn.textContent='…';
  const ok=await fetch(`/api/tasks/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'Done'})}).then(r=>r.json()).then(r=>r.ok).catch(()=>false);
  if(ok){btn.textContent='Done';btn.style.color='var(--grn)';btn.disabled=false;updateCardStatus(card,'Done');toast('Task marked done','success')}
  else{btn.textContent='✗ Error';btn.disabled=false}
}
async function markInProg(id,btn){
  const card=btn.closest('.tcard');
  btn.disabled=true;btn.textContent='…';
  const ok=await fetch(`/api/tasks/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'In progress'})}).then(r=>r.json()).then(r=>r.ok).catch(()=>false);
  if(ok){btn.textContent='In progress';btn.style.color='';btn.disabled=false;updateCardStatus(card,'In progress');toast('Task reopened','info')}
  else{btn.textContent='✗ Error';btn.disabled=false}
}"""

new_toggle = """async function toggleTaskDone(id,btn){
  const card=btn.closest('.tcard');
  const current=(card?.dataset.status||'').toLowerCase();
  if(current==='done') return markInProg(id,btn);
  return markDone(id,btn);
}
async function markDone(id,btn){
  const card=btn.closest('.tcard');
  if(btn){ btn.disabled=true; btn.textContent='…'; }
  const ok=await fetch(`/api/tasks/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'Done'})}).then(r=>r.json()).then(r=>r.ok).catch(()=>false);
  if(ok){
    if(btn){btn.textContent='✓';btn.disabled=false;}
    updateCardStatus(card,'Done');toast('Task marked done','success');
  }
  else{if(btn){btn.textContent='!';btn.disabled=false;}}
}
async function markInProg(id,btn){
  const card=btn.closest('.tcard');
  if(btn){ btn.disabled=true; btn.textContent='…'; }
  const ok=await fetch(`/api/tasks/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'In progress'})}).then(r=>r.json()).then(r=>r.ok).catch(()=>false);
  if(ok){
    if(btn){btn.textContent='';btn.disabled=false;}
    updateCardStatus(card,'In progress');toast('Task reopened','info');
  }
  else{if(btn){btn.textContent='!';btn.disabled=false;}}
}"""

# Fix noise removal
t = re.sub(r'<div id="noise"></div>', '', t)

# Fix top bar transparency
# .topbar{height:48px;padding:0 24px;display:flex;align-items:center;gap:10px;flex-shrink:0;border-bottom:1px solid rgba(255,255,255,0.06);background:rgba(5,5,5,.4);backdrop-filter:blur(30px);position:relative;z-index:10;}
# We change background to transparent and remove bottom-border/blur if they want it not visible/more transparent.
topbar_rgx = r'\.topbar\{[^}]+\}'
topbar_new = '.topbar{height:48px;padding:0 24px;display:flex;align-items:center;gap:10px;flex-shrink:0;background:transparent;position:relative;z-index:10;}'
t = re.sub(topbar_rgx, topbar_new, t)

# Fix task clipping
# .tcard-inner has height: 100%, causing clipping if padding is 24px + gap 16px etc.
# We change height: 100% to height: auto
t = t.replace('height: 100%;\n    position: relative;\n    z-index: 2;\n}', 'height: auto;\n    position: relative;\n    z-index: 2;\n}')

# replace old_toggle
t = t.replace(old_toggle, new_toggle)

with open("index.html", "w") as f:
    f.write(t)
print("done patching")
