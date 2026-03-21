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

const tokens = cleanContent.split(/(<?\/?[^>]+>)/g);

for (const token of tokens) {
  const openMatch = token.match(/^<(ul|ol|table|blockquote|pre|div|section)[\s>]/i);
  const closeMatch = token.match(/^<\/(ul|ol|table|blockquote|pre|div|section)>/i);

  if (openMatch) {
    depth++;
    if (isCompoundOpen(token)) compoundDepth++;
  }
  current += token;

  if (closeMatch) {
    depth--;
    if (compoundDepth > 0 && closeMatch[1].toLowerCase() === 'div') {
      compoundDepth--;
    }
    if (depth <= 0) {
      depth = 0;
      compoundDepth = 0;
      if (current.trim()) { topLevelBlocks.push(current); current = ''; }
    }
  } else if (depth === 0 && compoundDepth === 0) {
    const topCloseMatch = token.match(/^<\/(h[1-6]|p)>/i);
    if (topCloseMatch && current.trim()) { topLevelBlocks.push(current); current = ''; }
  }
}
if (current.trim()) topLevelBlocks.push(current);

topLevelBlocks.forEach((b, i) => {
  console.log(`\n\n--- BLOCK ${i} ---\n${b.trim()}`);
});
