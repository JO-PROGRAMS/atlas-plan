import re
from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

bg_pattern = re.compile(r"#bg-layer\s*\{.*?\n\}\n\n#bg-layer::before\s*\{.*?\n\}", re.DOTALL)

bg_repl = """#bg-layer {
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  background-color: #0B0F14;
  background:
    radial-gradient(1000px 760px at 18% 20%, rgba(91, 156, 255, 0.12) 0%, rgba(91, 156, 255, 0) 62%),
    radial-gradient(920px 820px at 82% 84%, rgba(120, 194, 255, 0.08) 0%, rgba(120, 194, 255, 0) 66%),
    radial-gradient(760px 620px at 78% 18%, rgba(160, 140, 255, 0.05) 0%, rgba(160, 140, 255, 0) 58%),
    radial-gradient(150% 110% at 50% 46%, rgba(20, 28, 36, 0) 38%, rgba(11, 15, 20, 0.62) 100%),
    linear-gradient(165deg, #10161D 0%, #0B0F14 54%, #141C24 100%);
  background-blend-mode: screen, screen, screen, multiply, normal;
  background-attachment: fixed;
  z-index: -2;
}

#bg-layer::before {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.82' numOctaves='2' seed='3'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  background-size: 220px 220px;
  pointer-events: none;
  z-index: 1;
}"""

s, n = bg_pattern.subn(bg_repl, s, count=1)

panel_anchor = "#p-tasks{background:transparent;position:relative;isolation:isolate;overflow:visible}\n#p-tasks::before{display:none}\n#p-tasks .ph{display:none}\n"
if panel_anchor in s and "#p-tasks .tc-desc," not in s:
    s = s.replace(
        panel_anchor,
        panel_anchor +
        "#p-tasks .tcard{width:100%;max-width:min(1120px,96%)}\n"
        "#p-tasks .tc-content-col{min-width:0}\n"
        "#p-tasks .tc-desc,\n"
        "#p-tasks .tc-sum{\n"
        "  max-width:100%;\n"
        "  overflow:hidden;\n"
        "  display:-webkit-box;\n"
        "  -webkit-line-clamp:4;\n"
        "  -webkit-box-orient:vertical;\n"
        "  white-space:normal;\n"
        "  line-height:1.5;\n"
        "}\n"
        "#p-tasks .tc-meta{max-width:92px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}\n"
    )

p.write_text(s, encoding='utf-8')
print('updated', n)
