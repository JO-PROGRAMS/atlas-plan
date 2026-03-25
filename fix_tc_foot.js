const fs = require('fs');
let html = fs.readFileSync('index.html', 'utf8');

html = html.replace('.tc-foot{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;position:relative;z-index:2}',
'.tc-foot{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;position:relative;z-index:2;margin-top:10px;margin-bottom:12px;}');

fs.writeFileSync('index.html', html);
