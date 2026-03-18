/**
 * Unit tests for the HTML compound block splitter in ArticleContentWithImages.
 * 
 * These tests verify that compound HTML structures (compare-grid, pros-cons,
 * spec-bar, etc.) are preserved as single blocks and never split into
 * separate article-element wrappers.
 * 
 * @jest-environment jsdom
 */

// ─── Extract the splitter logic for isolated testing ────────────────────────

const COMPOUND_CLASSES = [
  'compare-grid', 'compare-card', 'pros-cons', 'pc-block',
  'spec-bar', 'powertrain-specs', 'fm-verdict', 'price-tag',
  'seo-related-links',
];

function isCompoundOpen(token: string): boolean {
  const classMatch = token.match(/class=["']([^"']*)["']/);
  if (!classMatch) return false;
  const classes = classMatch[1].split(/\s+/);
  return classes.some(c => COMPOUND_CLASSES.some(prefix => c === prefix));
}

function splitIntoBlocks(html: string): string[] {
  const topLevelBlocks: string[] = [];
  let current = '';
  let depth = 0;
  let compoundDepth = 0;

  const tokens = html.split(/(<\/?[^>]+>)/g);

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
  return topLevelBlocks;
}

// ─── Tests ──────────────────────────────────────────────────────────────────

describe('splitIntoBlocks', () => {
  // ─── Basic splitting ─────────────────────────────────────

  it('splits paragraphs into separate blocks', () => {
    const html = '<p>First paragraph</p><p>Second paragraph</p>';
    const blocks = splitIntoBlocks(html);
    expect(blocks).toHaveLength(2);
    expect(blocks[0]).toContain('First paragraph');
    expect(blocks[1]).toContain('Second paragraph');
  });

  it('splits headings and paragraphs', () => {
    const html = '<h2>Title</h2><p>Content</p>';
    const blocks = splitIntoBlocks(html);
    expect(blocks).toHaveLength(2);
  });

  it('keeps a single div as one block', () => {
    const html = '<div class="simple">Content inside</div>';
    const blocks = splitIntoBlocks(html);
    expect(blocks).toHaveLength(1);
  });

  // ─── Compound structures must stay together ──────────────

  it('preserves compare-grid as a single block', () => {
    const html = `
      <div class="compare-grid">
        <div class="compare-card featured">
          <div class="compare-badge">This Vehicle</div>
          <div class="compare-card-name">2026 ZEEKR 8X</div>
          <div class="compare-row"><span class="k">Power</span><span class="v">885 hp</span></div>
          <div class="compare-row"><span class="k">EV Range</span><span class="v">410 km</span></div>
          <div class="compare-row"><span class="k">Price</span><span class="v">$54,600</span></div>
        </div>
        <div class="compare-card">
          <div class="compare-card-name">BMW X5 xDrive50e</div>
          <div class="compare-row"><span class="k">Power</span><span class="v">483 hp</span></div>
          <div class="compare-row"><span class="k">Price</span><span class="v">~$73,000</span></div>
        </div>
      </div>`;
    const blocks = splitIntoBlocks(html);
    expect(blocks).toHaveLength(1);
    expect(blocks[0]).toContain('compare-grid');
    expect(blocks[0]).toContain('BMW X5');
    expect(blocks[0]).toContain('$54,600');
  });

  it('preserves pros-cons as a single block', () => {
    const html = `
      <div class="pros-cons">
        <div class="pc-block pros">
          <div class="pc-title">Pros</div>
          <ul class="pc-list"><li>Fast</li><li>Efficient</li></ul>
        </div>
        <div class="pc-block cons">
          <div class="pc-title">Cons</div>
          <ul class="pc-list"><li>Heavy</li></ul>
        </div>
      </div>`;
    const blocks = splitIntoBlocks(html);
    expect(blocks).toHaveLength(1);
    expect(blocks[0]).toContain('pros-cons');
    expect(blocks[0]).toContain('Fast');
    expect(blocks[0]).toContain('Heavy');
  });

  it('preserves spec-bar as a single block', () => {
    const html = `
      <div class="spec-bar">
        <div class="spec-item"><div class="spec-label">PRICE</div><div class="spec-value">$54,600</div></div>
        <div class="spec-item"><div class="spec-label">RANGE</div><div class="spec-value">410 km</div></div>
      </div>`;
    const blocks = splitIntoBlocks(html);
    expect(blocks).toHaveLength(1);
  });

  it('preserves powertrain-specs as a single block', () => {
    const html = `
      <div class="powertrain-specs">
        <div class="ps-item"><div class="ps-label">PLATFORM</div><div class="ps-val">SEA-S 900V</div></div>
        <div class="ps-item"><div class="ps-label">POWER</div><div class="ps-val">1,381 hp</div></div>
      </div>`;
    const blocks = splitIntoBlocks(html);
    expect(blocks).toHaveLength(1);
  });

  it('preserves fm-verdict as a single block', () => {
    const html = `
      <div class="fm-verdict">
        <div class="verdict-label">FreshMotors Verdict</div>
        <p>This car is amazing.</p>
      </div>`;
    const blocks = splitIntoBlocks(html);
    expect(blocks).toHaveLength(1);
    expect(blocks[0]).toContain('fm-verdict');
  });

  // ─── Mixed content with compounds ────────────────────────

  it('splits around compound blocks correctly', () => {
    const html = `
      <p>Introduction paragraph</p>
      <div class="compare-grid">
        <div class="compare-card"><div class="compare-row"><span>data</span></div></div>
      </div>
      <p>Conclusion paragraph</p>`;
    const blocks = splitIntoBlocks(html);
    expect(blocks).toHaveLength(3);
    expect(blocks[0]).toContain('Introduction');
    expect(blocks[1]).toContain('compare-grid');
    expect(blocks[2]).toContain('Conclusion');
  });

  it('handles multiple compound blocks in sequence', () => {
    const html = `
      <div class="spec-bar"><div class="spec-item">A</div></div>
      <p>Middle text</p>
      <div class="pros-cons"><div class="pc-block pros"><ul><li>Good</li></ul></div></div>`;
    const blocks = splitIntoBlocks(html);
    expect(blocks).toHaveLength(3);
    expect(blocks[0]).toContain('spec-bar');
    expect(blocks[1]).toContain('Middle');
    expect(blocks[2]).toContain('pros-cons');
  });

  // ─── Edge cases ──────────────────────────────────────────

  it('handles empty content', () => {
    const blocks = splitIntoBlocks('');
    expect(blocks).toHaveLength(0);
  });

  it('handles non-compound nested divs normally', () => {
    const html = '<div class="wrapper"><div class="inner">Hello</div></div>';
    const blocks = splitIntoBlocks(html);
    expect(blocks).toHaveLength(1);
  });

  it('handles malformed HTML gracefully', () => {
    // Extra closing div — common in AI-generated content
    const html = '<div class="compare-grid"><div class="compare-card"></div></div></div><p>After</p>';
    const blocks = splitIntoBlocks(html);
    // Should not crash
    expect(blocks.length).toBeGreaterThanOrEqual(1);
  });

  it('handles compound class with extra classes', () => {
    const html = '<div class="compare-grid some-extra-class"><div class="compare-card featured"><div class="compare-row">data</div></div></div>';
    const blocks = splitIntoBlocks(html);
    expect(blocks).toHaveLength(1);
  });
});
