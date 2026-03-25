import re
html = open("index.html").read()
html = html.replace("${esc(String(t.status||'Not started'))}", "<span style=\"opacity:0.6;margin-right:3px;\">Status:</span>${esc(String(t.status||'Not started'))}")
html = html.replace("${esc(String(t.priority))}", "<span style=\"opacity:0.6;margin-right:3px;\">Priority:</span>${esc(String(t.priority))}")
html = html.replace("${esc(String(t.effort))}", "<span style=\"opacity:0.6;margin-right:3px;\">Effort:</span>${esc(String(t.effort))}")
html = html.replace("${esc(String(due))}", "<span style=\"opacity:0.6;margin-right:3px;\">Due:</span>${esc(String(due))}")
open("index.html","w").write(html)
