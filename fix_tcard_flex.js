const fs = require('fs');
let html = fs.readFileSync('index.html', 'utf8');

html = html.replace('.tgrid{', '.tgrid{\n  align-items:center;\n');
html = html.replace('.tcard{', '.tcard{\n  width:100%;\n  max-width:920px;\n  margin:0 auto;\n');

fs.writeFileSync('index.html', html);
console.log('Fixed tcard flex constraints');
