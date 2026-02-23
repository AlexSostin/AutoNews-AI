'use client';

import Image from 'next/image';
import { useEffect, useState, useRef, useCallback, type ReactElement } from 'react';

interface ArticleContentWithImagesProps {
  content: string;
  images: string[];
  imageSource?: string;
  authorName?: string;
}

/**
 * Strip hidden alt-texts div from content for clean rendering.
 */
function stripAltTextsDiv(html: string): string {
  return html.replace(/<div[^>]*class=["']alt-texts["'][^>]*>[\s\S]*?<\/div>/gi, '').trim();
}

export default function ArticleContentWithImages({ content, images, imageSource, authorName }: ArticleContentWithImagesProps) {
  const [contentParts, setContentParts] = useState<ReactElement[] | null>(null);

  // Prepare clean HTML for SSR fallback (strip alt-texts div)
  const cleanHtmlForSSR = stripAltTextsDiv(content);

  useEffect(() => {
    // Extract AI-generated alt texts from hidden div
    const altTexts: string[] = [];
    const altTextMatch = content.match(/<div[^>]*class=["']alt-texts["'][^>]*>([\s\S]*?)<\/div>/i);
    if (altTextMatch) {
      const altBlock = altTextMatch[1];
      const altLines = altBlock.match(/ALT_TEXT_\d+:\s*(.+)/g);
      if (altLines) {
        altLines.forEach(line => {
          const value = line.replace(/ALT_TEXT_\d+:\s*/, '').trim();
          if (value && value !== '[descriptive alt text' && !value.startsWith('[')) {
            altTexts.push(value);
          }
        });
      }
    }

    // Strip the alt-texts div from content before parsing
    const cleanContent = stripAltTextsDiv(content);

    const topLevelBlocks: string[] = [];
    let current = '';
    let depth = 0;

    const tokens = cleanContent.split(/(<?\/?[^>]+>)/g);

    for (const token of tokens) {
      const openMatch = token.match(/^<(ul|ol|table|blockquote|pre|div|section)[\s>]/i);
      const closeMatch = token.match(/^<\/(ul|ol|table|blockquote|pre|div|section)>/i);

      if (openMatch) depth++;
      current += token;

      if (closeMatch) {
        depth--;
        if (depth <= 0) {
          depth = 0;
          if (current.trim()) { topLevelBlocks.push(current); current = ''; }
        }
      } else if (depth === 0) {
        const topCloseMatch = token.match(/^<\/(h[1-6]|p)>/i);
        if (topCloseMatch && current.trim()) { topLevelBlocks.push(current); current = ''; }
      }
    }

    if (current.trim()) topLevelBlocks.push(current);

    const parts: ReactElement[] = [];
    let imageIndex = 0;
    let paragraphsSinceLastImage = 0;
    const PARAGRAPHS_BETWEEN_IMAGES = 3;

    topLevelBlocks.forEach((block, idx) => {
      if (block.trim()) {
        parts.push(
          <div key={`element-${idx}`} dangerouslySetInnerHTML={{ __html: block }} className="article-element" />
        );

        const isParagraph = /^<p[\s>]/i.test(block.trim());
        if (isParagraph) {
          paragraphsSinceLastImage++;
        }

        if (isParagraph && paragraphsSinceLastImage >= PARAGRAPHS_BETWEEN_IMAGES && imageIndex < images.length) {
          const currentImage = images[imageIndex];
          const altText = altTexts[imageIndex] || `Article image ${imageIndex + 1}`;

          parts.push(
            <InlineImage
              key={`img-${imageIndex}`}
              src={currentImage}
              alt={altText}
              imageSource={imageSource || (currentImage.includes('pexels.com') ? 'pexels' : 'unknown')}
              authorName={authorName}
            />
          );
          imageIndex++;
          paragraphsSinceLastImage = 0;
        }
      }
    });

    setContentParts(parts);
  }, [content, images]);

  return (
    <div className="article-content-wrapper">
      {contentParts !== null ? (
        /* Enhanced client version with inline images and lightbox */
        contentParts
      ) : (
        /* SSR fallback — raw article HTML visible to search engines, bots, and crawlers.
           This ensures Google/AdSense sees the full article text in the initial HTML response.
           It's replaced by the enhanced version after client-side hydration. */
        <div
          className="article-content"
          dangerouslySetInnerHTML={{ __html: cleanHtmlForSSR }}
          suppressHydrationWarning
        />
      )}
    </div>
  );
}

// ─── Inline image with lightbox + zoom/pan ────────────────────────────────────
function InlineImage({ src, alt, imageSource, authorName }: { src: string; alt: string; imageSource: string; authorName?: string }) {
  const [open, setOpen] = useState(false);
  const [imgError, setImgError] = useState(false);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  // Refs for window-level drag listeners
  const scaleRef = useRef(1);
  const offsetRef = useRef({ x: 0, y: 0 });
  const dragging = useRef(false);
  const startPos = useRef({ x: 0, y: 0 });
  const startOffset = useRef({ x: 0, y: 0 });
  const lastPinchDist = useRef<number | null>(null);
  const zoomContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => { scaleRef.current = scale; }, [scale]);
  useEffect(() => { offsetRef.current = offset; }, [offset]);

  const resetZoom = useCallback(() => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
    scaleRef.current = 1;
    offsetRef.current = { x: 0, y: 0 };
  }, []);

  useEffect(() => {
    if (!open) { resetZoom(); return; }
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    window.addEventListener('keydown', handler);
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', handler);
      document.body.style.overflow = '';
    };
  }, [open, resetZoom]);

  // Native wheel listener with { passive: false } to allow preventDefault
  useEffect(() => {
    if (!open) return;
    const el = zoomContainerRef.current;
    if (!el) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setScale(s => {
        const next = Math.min(5, Math.max(1, s - e.deltaY * 0.003));
        scaleRef.current = next;
        return next;
      });
    };

    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => el.removeEventListener('wheel', handleWheel);
  }, [open]);

  // Native touch listeners with { passive: false } to allow preventDefault
  useEffect(() => {
    if (!open) return;
    const el = zoomContainerRef.current;
    if (!el) return;

    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        const dx = e.touches[0].clientX - e.touches[1].clientX;
        const dy = e.touches[0].clientY - e.touches[1].clientY;
        lastPinchDist.current = Math.hypot(dx, dy);
      } else if (e.touches.length === 1 && scaleRef.current > 1) {
        dragging.current = true;
        startPos.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        startOffset.current = { ...offsetRef.current };
      }
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2 && lastPinchDist.current !== null) {
        e.preventDefault();
        const dx = e.touches[0].clientX - e.touches[1].clientX;
        const dy = e.touches[0].clientY - e.touches[1].clientY;
        const dist = Math.hypot(dx, dy);
        const ratio = dist / lastPinchDist.current;
        lastPinchDist.current = dist;
        setScale(s => {
          const next = Math.min(5, Math.max(1, s * ratio));
          scaleRef.current = next;
          return next;
        });
      } else if (e.touches.length === 1 && dragging.current) {
        const nx = startOffset.current.x + (e.touches[0].clientX - startPos.current.x);
        const ny = startOffset.current.y + (e.touches[0].clientY - startPos.current.y);
        offsetRef.current = { x: nx, y: ny };
        setOffset({ x: nx, y: ny });
      }
    };

    const handleTouchEnd = () => {
      dragging.current = false;
      lastPinchDist.current = null;
      if (scaleRef.current <= 1) resetZoom();
    };

    el.addEventListener('touchstart', handleTouchStart, { passive: true });
    el.addEventListener('touchmove', handleTouchMove, { passive: false });
    el.addEventListener('touchend', handleTouchEnd);

    return () => {
      el.removeEventListener('touchstart', handleTouchStart);
      el.removeEventListener('touchmove', handleTouchMove);
      el.removeEventListener('touchend', handleTouchEnd);
    };
  }, [open, resetZoom]);

  // Mouse drag — listeners on window to avoid losing track on fast moves
  const onMouseDown = (e: React.MouseEvent) => {
    if (scaleRef.current <= 1) return;
    e.preventDefault();
    dragging.current = true;
    startPos.current = { x: e.clientX, y: e.clientY };
    startOffset.current = { ...offsetRef.current };

    const onMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const nx = startOffset.current.x + (ev.clientX - startPos.current.x);
      const ny = startOffset.current.y + (ev.clientY - startPos.current.y);
      offsetRef.current = { x: nx, y: ny };
      setOffset({ x: nx, y: ny });
    };

    const onUp = () => {
      dragging.current = false;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  return (
    <>
      {/* Thumbnail button */}
      <button
        onClick={() => !imgError && setOpen(true)}
        className={`relative w-full my-10 rounded-2xl overflow-hidden shadow-2xl bg-gradient-to-br from-gray-50 to-gray-100 group focus:outline-none focus:ring-2 focus:ring-indigo-500 block text-left ${imgError ? 'cursor-default' : 'cursor-zoom-in'}`}
        aria-label={imgError ? 'Image unavailable' : 'Open image fullscreen'}
      >
        <div className="relative w-full aspect-video">
          {imgError ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-100 text-gray-400">
              <svg className="w-12 h-12 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z" />
                <line x1="4" y1="4" x2="20" y2="20" strokeWidth={1.5} />
              </svg>
              <span className="text-sm font-medium">Image unavailable</span>
            </div>
          ) : (
            <>
              <Image
                src={src} alt={alt} fill
                className="object-cover group-hover:scale-[1.02] transition-transform duration-300 !m-0 !shadow-none !rounded-none"
                unoptimized
                onError={() => setImgError(true)}
              />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-200 flex items-center justify-center">
                <svg className="w-10 h-10 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200 drop-shadow-lg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                </svg>
              </div>
            </>
          )}
        </div>
      </button>

      {/* Lightbox with zoom */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm"
          onClick={() => { if (scaleRef.current <= 1) setOpen(false); }}
        >
          {/* Top bar */}
          <div className="absolute top-0 left-0 right-0 flex items-center justify-end px-4 py-3 z-10 bg-gradient-to-b from-black/60 to-transparent pointer-events-none">
            <div className="flex items-center gap-2 pointer-events-auto">
              <button onClick={resetZoom} className="p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors" title="Reset zoom">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
              <button onClick={() => setOpen(false)} className="p-2 bg-white/10 hover:bg-white/25 rounded-full text-white transition-colors" aria-label="Close">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Zoom hints */}
          {scale === 1 && (
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 text-white/40 text-xs pointer-events-none select-none hidden md:block">
              Scroll to zoom · Drag to pan
            </div>
          )}
          {scale === 1 && (
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 text-white/40 text-xs pointer-events-none select-none md:hidden">
              Pinch to zoom · Drag to pan
            </div>
          )}

          {/* Zoomable image */}
          <div
            ref={zoomContainerRef}
            className="relative w-full h-full max-w-5xl max-h-[90vh] mx-8 overflow-hidden select-none"
            style={{ cursor: scale > 1 ? 'grab' : 'zoom-in' }}
            onMouseDown={onMouseDown}
            onClick={e => e.stopPropagation()}
          >
            <div
              style={{
                transform: `scale(${scale}) translate(${offset.x / scale}px, ${offset.y / scale}px)`,
                transition: scale === 1 ? 'transform 0.25s ease' : 'none',
                width: '100%',
                height: '100%',
                position: 'relative',
                willChange: 'transform',
              }}
            >
              <Image src={src} alt={alt} fill className="object-contain" unoptimized priority />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
