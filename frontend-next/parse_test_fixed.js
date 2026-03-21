const fs = require('fs');
const cleanContent = fs.readFileSync('../backend/article_content.html', 'utf8');

const COMPOUND_CLASSES = [
  'compare-grid', 'compare-card', 'pros-cons', 'pc-block',
  'spec-bar', 'powertrain-specs', 'fm-verdict', 'price-tag',
  'seo-related-links',
];

const isCompoundOpen = (token) => {
  const classMatch = token.match(/class=["']([^"']*)["']/);
  if (!classMatch) return false;
  const classes = classMatch[1].split(/\s+/);
  return classes.some(c => COMPOUND_CLASSES.some(prefix => c === prefix));
};

const topLevelBlocks = [];
let current = '';
let depth = 0;
let compoundDepth = 0;
const stack = [];

const tokens = cleanContent.split(/(<?\/?[^>]+>)/g);

let i = 0;
for (const token of tokens) {
  if (!token.trim()) continue;
  
  const openMatch = token.match(/^<(ul|ol|table|blockquote|pre|div|section)[\s>]/i);
  const closeMatch = token.match(/^<\/(ul|ol|table|blockquote|pre|div|section)>/i);

  if (openMatch) {
    depth++;
    const compound = isCompoundOpen(token);
    stack.push(compound);
    if (compound) compoundDepth++;
    console.log(`[+] OPEN: ${token.trim().substring(0, 30)} | depth=${depth} compoundDepth=${compoundDepth} stack=[${stack.map(v => v?'1':'0').join('')}]`);
  } else if (closeMatch) {
    depth--;
    const wasCompound = stack.pop();
    if (wasCompound) {
      compoundDepth--;
    }
    console.log(`[-] CLOSE: ${token.trim()} | depth=${depth} compoundDepth=${compoundDepth} wasC=${wasCompound}`);
    if (depth <= 0) {
      depth = 0;
      compoundDepth = 0;
      stack.length = 0;
      if (current.trim()) { topLevelBlocks.push(current); current = ''; console.log(`>>> SHIFTING BLOCK (depth 0) <<<`);}
    }
  } else {
    // console.log(`[~] TEXT: ${token.substring(0, 30)}... | depth=${depth} compoundDepth=${compoundDepth}`);
    if (depth === 0 && compoundDepth === 0) {
      const topCloseMatch = token.match(/^<\/(h[1-6]|p)>/i);
      if (topCloseMatch && current.trim()) { topLevelBlocks.push(current); current = ''; console.log(`>>> SHIFTING BLOCK (top p/h) <<<`);}
    }
  }
  current += token;
}
if (current.trim()) topLevelBlocks.push(current);

topLevelBlocks.forEach((b, i) => {
  console.log(`\n\n--- BLOCK ${i} ---\n${b.trim()}`);
});
