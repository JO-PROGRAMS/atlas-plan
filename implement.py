import re

with open("index.html", "r") as f:
    content = f.read()

# Add logic for FLIP
content = re.sub(
    r"container\.addEventListener\('dragover',\s*e=>\s*\{[^}]*updateDragFx[^}]*const\s+afterEl\s*=\s*dragAfterElement\([^}]*\}\s*\);\s*\}\s*container\.insertBefore[^}]*\}\s*\);",
    r"""container.addEventListener('dragover', e => {
      e.preventDefault();
      const dragging = container.querySelector('.dragging');
      if (!dragging) return;
      updateDragFx(dragging, e.clientX, e.clientY);
      
      const afterEl = dragAfterElement(e.clientY);
      if (afterEl == null) {
        container.appendChild(dragging);
        return;
      }
      container.insertBefore(dragging, afterEl);
    });""",
    content
)

with open("index.html", "w") as f:
    f.write(content)
print("FLIP script executed")
