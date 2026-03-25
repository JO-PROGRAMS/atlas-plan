import re
with open("index.html", "r") as f:
    t = f.read()

# Replace toggleTaskDone
pattern_toggle = r'async function toggleTaskDone\(id,btn\)\{[\s\S]*?async function markDone\(id,btn\)\{'
new_toggle = """async function toggleTaskDone(id,btn){
  const card=btn.closest('.tcard');
  const current=(card?.dataset.status||'').toLowerCase();
  if(current==='done') return markInProg(id,btn);
  return markDone(id,btn);
}
async function markDone(id,btn){"""
t = re.sub(pattern_toggle, new_toggle, t)

# Provide fallback if `btn` doesn't have textContent right away or we just restyle the check.
pattern_markDone = r'async function markDone\(id,btn\)\{[\s\S]*?\}\s*async function markInProg\(id,btn\)\{'
new_markDone = """async function markDone(id,btn){
  const card=btn.closest('.tcard');
  if(btn){ btn.disabled=true; }
  const ok=await fetch(`/api/tasks/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'Done'})}).then(r=>r.json()).then(r=>r.ok).catch(()=>false);
  if(ok){
    if(btn){btn.disabled=false;}
    updateCardStatus(card,'Done');toast('Task marked done','success');
  } else {
    if(btn){btn.disabled=false;}
    toast('Error','error');
  }
}
async function markInProg(id,btn){"""
t = re.sub(pattern_markDone, new_markDone, t)

pattern_markInProg = r'async function markInProg\(id,btn\)\{[\s\S]*?\}\s*async function deleteTask\(id,btn\)\{'
new_markInProg = """async function markInProg(id,btn){
  const card=btn.closest('.tcard');
  if(btn){ btn.disabled=true; }
  const ok=await fetch(`/api/tasks/${id}/status`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'In progress'})}).then(r=>r.json()).then(r=>r.ok).catch(()=>false);
  if(ok){
    if(btn){btn.disabled=false;}
    updateCardStatus(card,'In progress');toast('Task updated','info');
  } else {
    if(btn){btn.disabled=false;}
    toast('Error','error');
  }
}
async function deleteTask(id,btn){"""
t = re.sub(pattern_markInProg, new_markInProg, t)

with open("index.html", "w") as f:
    f.write(t)
print("Done logic patched.")
