'use client';

import { useEffect, useCallback, useState, useRef } from 'react';
import Image from 'next/image';
import { X, ChevronLeft, ChevronRight, ZoomIn, RotateCcw } from 'lucide-react';

interface LightboxImage {
    url: string;
    alt: string;
}

interface ImageLightboxProps {
    images: LightboxImage[];
}

// ─── Zoom + Pan hook ──────────────────────────────────────────────────────────
function useZoomPan(isOpen: boolean) {
    const [scale, setScale] = useState(1);
    const [offset, setOffset] = useState({ x: 0, y: 0 });
    const dragging = useRef(false);
    const startPos = useRef({ x: 0, y: 0 });
    const startOffset = useRef({ x: 0, y: 0 });
    const lastPinchDist = useRef<number | null>(null);
    const scaleRef = useRef(1);
    const offsetRef = useRef({ x: 0, y: 0 });

    // Keep refs in sync so window listeners can read latest values
    useEffect(() => { scaleRef.current = scale; }, [scale]);
    useEffect(() => { offsetRef.current = offset; }, [offset]);

    const reset = useCallback(() => {
        setScale(1);
        setOffset({ x: 0, y: 0 });
        scaleRef.current = 1;
        offsetRef.current = { x: 0, y: 0 };
    }, []);

    useEffect(() => { if (!isOpen) reset(); }, [isOpen, reset]);

    // ── Mouse wheel zoom ──
    const onWheel = useCallback((e: React.WheelEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setScale(s => {
            const next = Math.min(5, Math.max(1, s - e.deltaY * 0.003));
            scaleRef.current = next;
            return next;
        });
    }, []);

    // ── Mouse drag — attach to window so fast moves don't lose tracking ──
    const onMouseDown = useCallback((e: React.MouseEvent) => {
        if (scaleRef.current <= 1) return;
        e.preventDefault();
        dragging.current = true;
        startPos.current = { x: e.clientX, y: e.clientY };
        startOffset.current = { ...offsetRef.current };

        const onMove = (ev: MouseEvent) => {
            if (!dragging.current) return;
            const dx = ev.clientX - startPos.current.x;
            const dy = ev.clientY - startPos.current.y;
            const nx = startOffset.current.x + dx;
            const ny = startOffset.current.y + dy;
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
    }, []);

    // ── Touch pinch + pan ──
    const onTouchStart = useCallback((e: React.TouchEvent) => {
        if (e.touches.length === 2) {
            const dx = e.touches[0].clientX - e.touches[1].clientX;
            const dy = e.touches[0].clientY - e.touches[1].clientY;
            lastPinchDist.current = Math.hypot(dx, dy);
        } else if (e.touches.length === 1 && scaleRef.current > 1) {
            dragging.current = true;
            startPos.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
            startOffset.current = { ...offsetRef.current };
        }
    }, []);

    const onTouchMove = useCallback((e: React.TouchEvent) => {
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
            const dx = e.touches[0].clientX - startPos.current.x;
            const dy = e.touches[0].clientY - startPos.current.y;
            const nx = startOffset.current.x + dx;
            const ny = startOffset.current.y + dy;
            offsetRef.current = { x: nx, y: ny };
            setOffset({ x: nx, y: ny });
        }
    }, []);

    const onTouchEnd = useCallback(() => {
        dragging.current = false;
        lastPinchDist.current = null;
        if (scaleRef.current <= 1) reset();
    }, [reset]);

    return { scale, offset, reset, onWheel, onMouseDown, onTouchStart, onTouchMove, onTouchEnd };
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function ImageLightbox({ images }: ImageLightboxProps) {
    const [activeIndex, setActiveIndex] = useState<number | null>(null);
    const isOpen = activeIndex !== null;
    const zoom = useZoomPan(isOpen);

    const open = (index: number) => setActiveIndex(index);
    const close = () => setActiveIndex(null);

    const prev = useCallback(() => {
        zoom.reset();
        setActiveIndex(i => (i === null ? null : (i - 1 + images.length) % images.length));
    }, [images.length, zoom]);

    const next = useCallback(() => {
        zoom.reset();
        setActiveIndex(i => (i === null ? null : (i + 1) % images.length));
    }, [images.length, zoom]);

    // Keyboard
    useEffect(() => {
        if (!isOpen) return;
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') close();
            if (zoom.scale <= 1) {
                if (e.key === 'ArrowLeft') prev();
                if (e.key === 'ArrowRight') next();
            }
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [isOpen, prev, next, zoom.scale]);

    // Body scroll lock
    useEffect(() => {
        document.body.style.overflow = isOpen ? 'hidden' : '';
        return () => { document.body.style.overflow = ''; };
    }, [isOpen]);

    const gridCols =
        images.length === 1 ? 'md:grid-cols-1 max-w-2xl mx-auto'
            : images.length === 2 ? 'md:grid-cols-2'
                : images.length <= 4 ? 'md:grid-cols-3'
                    : 'md:grid-cols-3 lg:grid-cols-4';

    return (
        <>
            {/* Mobile slider */}
            <div className="md:hidden">
                <div className="flex gap-3 overflow-x-auto snap-x snap-mandatory scrollbar-hide pb-4 -mx-4 px-4">
                    {images.map((img, index) => (
                        <button
                            key={index}
                            onClick={() => open(index)}
                            className="relative flex-shrink-0 w-[85vw] aspect-video rounded-lg overflow-hidden snap-center group focus:outline-none"
                            aria-label={`Open image ${index + 1}`}
                        >
                            <Image src={img.url} alt={img.alt} fill className="object-cover group-hover:scale-105 transition-transform duration-300" unoptimized />
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
                                <ZoomIn className="text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" size={32} />
                            </div>
                            <div className="absolute bottom-2 left-2 bg-black/60 text-white text-xs px-2 py-1 rounded">
                                {index + 1} / {images.length}
                            </div>
                        </button>
                    ))}
                </div>
                <p className="text-center text-gray-500 text-sm mt-2">← Swipe to see more →</p>
            </div>

            {/* Desktop grid */}
            <div className={`hidden md:grid gap-4 ${gridCols}`}>
                {images.map((img, index) => (
                    <button
                        key={index}
                        onClick={() => open(index)}
                        className="relative aspect-video rounded-lg overflow-hidden group focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        aria-label={`Open image ${index + 1}`}
                    >
                        <Image src={img.url} alt={img.alt} fill className="object-cover group-hover:scale-105 transition-transform duration-300" unoptimized />
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/25 transition-colors flex items-center justify-center">
                            <ZoomIn className="text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" size={36} />
                        </div>
                    </button>
                ))}
            </div>

            {/* ── Lightbox ── */}
            {isOpen && activeIndex !== null && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm"
                    onClick={() => { if (zoom.scale <= 1) close(); }}
                >
                    {/* Top bar */}
                    <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-4 py-3 z-10 bg-gradient-to-b from-black/60 to-transparent pointer-events-none">
                        <span className="text-white/70 text-sm font-medium">{activeIndex + 1} / {images.length}</span>
                        <div className="flex items-center gap-2 pointer-events-auto">
                            <button
                                onClick={zoom.reset}
                                className="p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors"
                                title="Reset zoom"
                            >
                                <RotateCcw size={18} />
                            </button>
                            <button onClick={close} className="p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors" aria-label="Close">
                                <X size={22} />
                            </button>
                        </div>
                    </div>

                    {/* Zoom hints */}
                    {zoom.scale === 1 && (
                        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 text-white/40 text-xs pointer-events-none select-none hidden md:block">
                            Scroll to zoom · Drag to pan
                        </div>
                    )}
                    {zoom.scale === 1 && (
                        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 text-white/40 text-xs pointer-events-none select-none md:hidden">
                            Pinch to zoom · Drag to pan
                        </div>
                    )}

                    {/* Prev */}
                    {images.length > 1 && zoom.scale <= 1 && (
                        <button
                            onClick={e => { e.stopPropagation(); prev(); }}
                            className="absolute left-2 sm:left-6 z-10 p-2 sm:p-3 bg-white/10 hover:bg-white/25 rounded-full text-white transition-colors"
                            aria-label="Previous image"
                        >
                            <ChevronLeft size={28} />
                        </button>
                    )}

                    {/* Image + zoom area */}
                    <div
                        className="relative w-full h-full max-w-5xl max-h-[90vh] mx-12 sm:mx-20 overflow-hidden select-none"
                        style={{ cursor: zoom.scale > 1 ? 'grab' : 'zoom-in' }}
                        onWheel={zoom.onWheel}
                        onMouseDown={zoom.onMouseDown}
                        onTouchStart={zoom.onTouchStart}
                        onTouchMove={zoom.onTouchMove}
                        onTouchEnd={zoom.onTouchEnd}
                        onClick={e => e.stopPropagation()}
                    >
                        <div
                            style={{
                                width: '100%',
                                height: '100%',
                                position: 'relative',
                                transform: `scale(${zoom.scale}) translate(${zoom.offset.x / zoom.scale}px, ${zoom.offset.y / zoom.scale}px)`,
                                transition: zoom.scale === 1 ? 'transform 0.25s ease' : 'none',
                                willChange: 'transform',
                            }}
                        >
                            <Image
                                src={images[activeIndex].url}
                                alt={images[activeIndex].alt}
                                fill
                                className="object-contain"
                                unoptimized
                                priority
                            />
                        </div>
                    </div>

                    {/* Next */}
                    {images.length > 1 && zoom.scale <= 1 && (
                        <button
                            onClick={e => { e.stopPropagation(); next(); }}
                            className="absolute right-2 sm:right-6 z-10 p-2 sm:p-3 bg-white/10 hover:bg-white/25 rounded-full text-white transition-colors"
                            aria-label="Next image"
                        >
                            <ChevronRight size={28} />
                        </button>
                    )}

                    {/* Thumbnails */}
                    {images.length > 1 && zoom.scale <= 1 && (
                        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 px-4">
                            {images.map((img, i) => (
                                <button
                                    key={i}
                                    onClick={e => { e.stopPropagation(); zoom.reset(); setActiveIndex(i); }}
                                    className={`relative w-12 h-8 sm:w-16 sm:h-10 rounded overflow-hidden flex-shrink-0 transition-all duration-200 ${i === activeIndex ? 'ring-2 ring-white scale-110' : 'opacity-50 hover:opacity-80'
                                        }`}
                                    aria-label={`Go to image ${i + 1}`}
                                >
                                    <Image src={img.url} alt={img.alt} fill className="object-cover" unoptimized />
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </>
    );
}
