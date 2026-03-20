import React, { useCallback, useRef, useState } from 'react';
import { Loader2, Search, Wand2, Maximize2, Video, Upload, ChevronDown, GripVertical, ArrowLeftRight, ImageIcon, Plus, X } from 'lucide-react';
import api from '@/lib/api';

/* ═══════════════════════════════════════════════════════════════════════
   ArticleImageManager — Unified grid: all cards identical
   · Slot 1   = Cover (main article thumbnail)
   · Slot 2-3 = Body Inline (auto-inserted between sections)
   · Slot 4+  = Gallery (auto-synced to article-images API)
   · Drag-to-swap between ANY two slots (incl. gallery↔main)
   · Add More → appends new gallery slot
   ═══════════════════════════════════════════════════════════════════════ */

interface ArticleFormData {
    title: string;
    slug: string;
    summary: string;
    content: string;
    category_ids: number[];
    tags: number[];
    published: boolean;
    is_hero: boolean;
    is_news_only: boolean;
    youtube_url: string;
    author_name: string;
    author_channel_url: string;
    show_source: boolean;
    show_youtube: boolean;
    show_price: boolean;
    current_image: string;
    current_image_2: string;
    current_image_3: string;
    image: File | null;
    image_2: File | null;
    image_3: File | null;
    delete_image: boolean;
    delete_image_2: boolean;
    delete_image_3: boolean;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;
}

export interface GallerySlot {
    id: number;        // server-side article-image ID (0 = pending upload)
    url: string;       // current URL
    file?: File;       // staged upload
    pendingDelete?: boolean;
}

interface ArticleImageManagerProps {
    formData: ArticleFormData;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    setFormData: React.Dispatch<React.SetStateAction<any>>;
    imageSource: string;
    setImageSource: (source: string) => void;
    setPreviewImage: (url: string | null) => void;
    openPhotoSearch: (slot: number) => void;
    photoSearchLoading: boolean;
    generateAIImage: (slot: number, style: string, mode: 'auto' | 'custom', customPrompt: string) => Promise<void>;
    generatingAI: number | null;
    restoreYouTubeThumbnail: () => Promise<void>;
    restoringYT: boolean;
    articleId?: string | null;
    // Legacy props (kept for compat but no longer renders GallerySection separately)
    galleryImages?: { id: number; image: string; caption: string }[];
    onPickFromGallery?: (galleryImageId: number, galleryImageUrl: string, targetSlot: number) => void;
    onSlotChange?: (slot: number, oldUrl: string | null, newUrl: string | null) => void;
}

// ── Image metadata ────────────────────────────────────────────────────────
function ImageMeta({ src }: { src: string }) {
    const [meta, setMeta] = useState<{ w: number; h: number; size?: string } | null>(null);
    const imgRef = useRef<HTMLImageElement>(null);
    const handleLoad = useCallback(() => {
        const img = imgRef.current;
        if (img) setMeta(prev => ({ ...prev, w: img.naturalWidth, h: img.naturalHeight, size: prev?.size }));
    }, []);
    React.useEffect(() => {
        if (!src || !src.startsWith('http')) return;
        const ctrl = new AbortController();
        fetch(src, { method: 'HEAD', signal: ctrl.signal })
            .then(res => {
                const len = res.headers.get('content-length');
                if (len) {
                    const kb = Math.round(parseInt(len) / 1024);
                    setMeta(prev => (prev ? { ...prev, size: kb > 1024 ? `${(kb / 1024).toFixed(1)}MB` : `${kb}KB` } : { w: 0, h: 0, size: `${kb}KB` }));
                }
            })
            .catch(() => { });
        return () => ctrl.abort();
    }, [src]);
    return (
        <>
            <img ref={imgRef} src={src} onLoad={handleLoad} alt="" className="hidden" />
            {meta && (meta.w > 0 || meta.size) && (
                <div className="text-[10px] text-gray-400 mt-1 font-mono">
                    {meta.w > 0 && `${meta.w}×${meta.h}`}{meta.w > 0 && meta.size && ' • '}{meta.size}
                </div>
            )}
        </>
    );
}

// ── Action dropdown ───────────────────────────────────────────────────────
function SlotActions({
    slot, hasImage, hasYoutubeUrl,
    onUpload, onFindPhoto, onAIGenerate, onYouTubeRestore,
    photoSearchLoading, generatingAI, restoringYT, canGenerateAI,
}: {
    slot: number; hasImage: boolean; hasYoutubeUrl: boolean;
    onUpload: () => void; onFindPhoto: () => void;
    onAIGenerate: (style: string, mode: 'auto' | 'custom', prompt: string) => void;
    onYouTubeRestore: () => void;
    photoSearchLoading: boolean; generatingAI: number | null; restoringYT: boolean; canGenerateAI: boolean;
}) {
    const [open, setOpen] = useState(false);
    const [showAI, setShowAI] = useState(false);
    const [aiMode, setAiMode] = useState<'auto' | 'custom'>('auto');
    const [aiStyle, setAiStyle] = useState('scenic_road');
    const [aiCustomPrompt, setAiCustomPrompt] = useState('');
    const dropdownRef = useRef<HTMLDivElement>(null);

    const aiStyles = [
        { key: 'scenic_road', label: '🏔️ Scenic Road' }, { key: 'desert_sunset', label: '🌅 Desert Sunset' },
        { key: 'urban_city', label: '🌃 Urban City' }, { key: 'mountain_pass', label: '⛰️ Mountain Pass' },
        { key: 'studio', label: '📸 Studio' }, { key: 'coastal', label: '🌊 Coastal' },
        { key: 'forest', label: '🌲 Forest' }, { key: 'showroom', label: '✨ Showroom' },
    ];

    React.useEffect(() => {
        if (!open) return;
        const handler = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setOpen(false); setShowAI(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [open]);

    const isLoading = generatingAI === slot || photoSearchLoading || restoringYT;

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                type="button"
                onClick={() => { setOpen(!open); setShowAI(false); }}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-indigo-500 to-blue-600 text-white rounded-lg hover:from-indigo-600 hover:to-blue-700 transition-all text-sm font-medium disabled:opacity-50 shadow-sm w-full justify-center"
            >
                {isLoading
                    ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Working...</>
                    : <>{hasImage ? 'Replace' : 'Add Image'} <ChevronDown className="w-3.5 h-3.5" /></>
                }
            </button>

            {open && (
                <div className="absolute z-50 top-full mt-1 left-0 right-0 bg-white rounded-xl shadow-xl border border-gray-200 min-w-[220px]">
                    <label className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-gray-50 cursor-pointer transition-colors text-sm text-gray-700 rounded-t-xl">
                        <Upload className="w-4 h-4 text-gray-500" />
                        <span>📁 Upload from device</span>
                        <input type="file" accept="image/*" onChange={() => { onUpload(); setOpen(false); }} className="hidden" />
                    </label>

                    <button type="button" onClick={() => { onFindPhoto(); setOpen(false); }} disabled={photoSearchLoading}
                        className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-gray-50 transition-colors text-sm text-gray-700 w-full text-left disabled:opacity-50">
                        <Search className="w-4 h-4 text-emerald-500" />
                        <span>🔍 Find Photo (Pexels)</span>
                    </button>

                    <button type="button" onClick={() => setShowAI(!showAI)} disabled={!canGenerateAI || generatingAI !== null}
                        className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-gray-50 transition-colors text-sm text-gray-700 w-full text-left disabled:opacity-50">
                        <Wand2 className="w-4 h-4 text-purple-500" />
                        <span>🎨 AI Generate</span>
                        {!canGenerateAI && <span className="text-[10px] text-gray-400 ml-auto">needs img</span>}
                    </button>

                    {showAI && canGenerateAI && (
                        <div className="border-t border-gray-100 bg-purple-50/50 px-4 py-3 space-y-2">
                            <div className="flex gap-1">
                                <button type="button" onClick={() => setAiMode('auto')} className={`px-2.5 py-1 text-xs font-bold rounded-l-lg border ${aiMode === 'auto' ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-purple-600 border-purple-300'}`}>🚗 Auto</button>
                                <button type="button" onClick={() => setAiMode('custom')} className={`px-2.5 py-1 text-xs font-bold rounded-r-lg border-t border-b border-r ${aiMode === 'custom' ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-purple-600 border-purple-300'}`}>✏️ Custom</button>
                            </div>
                            {aiMode === 'auto' && (
                                <select value={aiStyle} onChange={(e) => setAiStyle(e.target.value)} className="w-full px-2 py-1.5 text-xs border border-purple-300 rounded-lg bg-white text-gray-800 outline-none">
                                    {aiStyles.map(s => <option key={s.key} value={s.key}>{s.label}</option>)}
                                </select>
                            )}
                            {aiMode === 'custom' && (
                                <input type="text" value={aiCustomPrompt} onChange={(e) => setAiCustomPrompt(e.target.value)} placeholder="Describe the image..." className="w-full px-2 py-1.5 text-xs border border-purple-300 rounded-lg bg-white text-gray-800 outline-none placeholder:text-gray-400" />
                            )}
                            <button type="button" onClick={() => { onAIGenerate(aiStyle, aiMode, aiCustomPrompt); setOpen(false); setShowAI(false); }}
                                className="w-full px-3 py-1.5 bg-purple-600 text-white rounded-lg text-xs font-bold hover:bg-purple-700 transition-colors">
                                {generatingAI === slot ? 'Generating...' : '✨ Generate'}
                            </button>
                        </div>
                    )}

                    {slot === 1 && hasYoutubeUrl && (
                        <button type="button" onClick={() => { onYouTubeRestore(); setOpen(false); }} disabled={restoringYT || generatingAI !== null}
                            className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-gray-50 transition-colors text-sm text-gray-700 w-full text-left disabled:opacity-50 border-t border-gray-100">
                            <Video className="w-4 h-4 text-red-500" />
                            <span>🎥 YouTube Thumbnail</span>
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}

// ── Slot label helpers ────────────────────────────────────────────────────
function getSlotLabel(slot: number) {
    if (slot === 1) return { label: `Image 1 — Cover`, sublabel: 'Main article thumbnail' };
    if (slot === 2) return { label: `Image 2 — Body Inline`, sublabel: 'Auto-inserted between sections' };
    if (slot === 3) return { label: `Image 3 — Body Inline`, sublabel: 'Auto-inserted between sections' };
    return { label: `Image ${slot} — Gallery`, sublabel: 'Appears in Vehicle Gallery' };
}

// ── Unified image card ────────────────────────────────────────────────────
type MainCard = {
    kind: 'main';
    slotIndex: number;   // 0-based index into main slots array
    slot: number;        // 1-based slot number (1=cover, 2-3=inline)
    currentKey: string;
    fileKey: string;
    deleteKey: string;
};
type GalleryCard = {
    kind: 'gallery';
    galleryIndex: number;  // index into gallerySlots state
    gallerySlot: GallerySlot;
};
type UnifiedCard = MainCard | GalleryCard;

// ── Main component ────────────────────────────────────────────────────────
export function ArticleImageManager({
    formData, setFormData, imageSource, setImageSource,
    setPreviewImage, openPhotoSearch, photoSearchLoading,
    generateAIImage, generatingAI, restoreYouTubeThumbnail,
    restoringYT, articleId, onSlotChange,
}: ArticleImageManagerProps) {

    const [dragSource, setDragSource] = useState<number | null>(null);
    const [dragOver, setDragOver] = useState<number | null>(null);
    const [gallerySlots, setGallerySlots] = useState<GallerySlot[]>([]);
    const [uploadingGallery, setUploadingGallery] = useState(false);
    const fileInputRefs = useRef<(HTMLInputElement | null)[]>([]);

    // Main slot config (fixed 3 positions)
    const mainSlots = [
        { slot: 1, currentKey: 'current_image', fileKey: 'image', deleteKey: 'delete_image' },
        { slot: 2, currentKey: 'current_image_2', fileKey: 'image_2', deleteKey: 'delete_image_2' },
        { slot: 3, currentKey: 'current_image_3', fileKey: 'image_3', deleteKey: 'delete_image_3' },
    ];

    // Fetch gallery from server on mount / articleId change
    React.useEffect(() => {
        if (!articleId) return;
        api.get(`/article-images/?article=${articleId}`)
            .then(res => {
                const imgs: { id: number; image: string }[] = res.data.results || res.data || [];
                setGallerySlots(imgs.map(img => ({
                    id: img.id,
                    url: img.image.startsWith('http') ? img.image : `https://heroic-healing-production-2365.up.railway.app${img.image}`,
                })));
            })
            .catch(() => { });
    }, [articleId]);

    // Build unified flat card list: [main1, main2, main3, gallery4, gallery5, ...]
    const totalCards = mainSlots.length + gallerySlots.length;

    const getCardType = (cardIdx: number): UnifiedCard => {
        if (cardIdx < mainSlots.length) {
            const s = mainSlots[cardIdx];
            return { kind: 'main', slotIndex: cardIdx, slot: s.slot, currentKey: s.currentKey, fileKey: s.fileKey, deleteKey: s.deleteKey };
        }
        const gi = cardIdx - mainSlots.length;
        return { kind: 'gallery', galleryIndex: gi, gallerySlot: gallerySlots[gi] };
    };

    // Swap two cards (any combination of main / gallery)
    const swapCards = (aIdx: number, bIdx: number) => {
        if (aIdx === bIdx) return;
        const cardA = getCardType(aIdx);
        const cardB = getCardType(bIdx);

        if (cardA.kind === 'main' && cardB.kind === 'main') {
            // main ↔ main
            const sA = mainSlots[cardA.slotIndex];
            const sB = mainSlots[cardB.slotIndex];
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            setFormData((prev: any) => ({
                ...prev,
                [sA.currentKey]: prev[sB.currentKey], [sA.fileKey]: prev[sB.fileKey], [sA.deleteKey]: prev[sB.deleteKey],
                [sB.currentKey]: prev[sA.currentKey], [sB.fileKey]: prev[sA.fileKey], [sB.deleteKey]: prev[sA.deleteKey],
            }));
        } else if (cardA.kind === 'main' && cardB.kind === 'gallery') {
            // main ↔ gallery: promote gallery into main, demote main to gallery
            const sA = mainSlots[cardA.slotIndex];
            const gB = cardB.gallerySlot;
            const mainUrl = (formData[sA.currentKey] as string) || '';
            const mainFile = (formData[sA.fileKey] as File | null) || null;
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            setFormData((prev: any) => ({ ...prev, [sA.currentKey]: gB.url, [sA.fileKey]: null, [sA.deleteKey]: false }));
            setGallerySlots(prev => {
                const updated = [...prev];
                updated[cardB.galleryIndex] = { id: gB.id, url: mainUrl || (mainFile ? URL.createObjectURL(mainFile) : ''), file: mainFile || undefined };
                return updated;
            });
        } else if (cardA.kind === 'gallery' && cardB.kind === 'main') {
            swapCards(bIdx, aIdx);
        } else if (cardA.kind === 'gallery' && cardB.kind === 'gallery') {
            // gallery ↔ gallery: just reorder in state
            setGallerySlots(prev => {
                const updated = [...prev];
                [updated[cardA.galleryIndex], updated[cardB.galleryIndex]] = [updated[cardB.galleryIndex], updated[cardA.galleryIndex]];
                return updated;
            });
        }
    };

    // File drop onto any card
    const handleFileDrop = (e: React.DragEvent, cardIdx: number) => {
        e.preventDefault();
        setDragOver(null);
        const file = e.dataTransfer.files?.[0];
        if (!file || !file.type.startsWith('image/')) return;
        placeFileInCard(cardIdx, file);
    };

    const placeFileInCard = (cardIdx: number, file: File) => {
        const card = getCardType(cardIdx);
        if (card.kind === 'main') {
            const s = mainSlots[card.slotIndex];
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            setFormData((prev: any) => ({ ...prev, [s.fileKey]: file, [s.deleteKey]: false }));
            if (card.slotIndex === 0) setImageSource('uploaded');
        } else {
            // Stage file for gallery slot (uploaded on save)
            setGallerySlots(prev => {
                const updated = [...prev];
                updated[card.galleryIndex] = { ...updated[card.galleryIndex], file, url: URL.createObjectURL(file) };
                return updated;
            });
        }
    };

    // Upload staged gallery files to server
    const flushGalleryUploads = async () => {
        if (!articleId) return;
        await Promise.all(
            gallerySlots.map(async (gs, i) => {
                if (!gs.file) return;
                const fd = new FormData();
                fd.append('article', articleId);
                fd.append('image', gs.file);
                fd.append('order', String(i));
                try {
                    const res = await api.post('/article-images/', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
                    setGallerySlots(prev => {
                        const updated = [...prev];
                        updated[i] = { id: res.data.id, url: res.data.image };
                        return updated;
                    });
                } catch (err) {
                    console.error('Gallery upload failed:', err);
                }
            })
        );
    };
    // Expose flush to parent if needed (via effect)
    React.useEffect(() => {
        // Auto-flush staged gallery when articleId becomes available (e.g., after create)
        if (articleId && gallerySlots.some(g => g.file && g.id === 0)) {
            flushGalleryUploads();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [articleId]);

    const addGallerySlot = async (files?: FileList | null) => {
        if (!files || files.length === 0) return;
        if (articleId) {
            // Upload immediately
            setUploadingGallery(true);
            try {
                await Promise.all(Array.from(files).map(async file => {
                    const fd = new FormData();
                    fd.append('article', articleId);
                    fd.append('image', file);
                    fd.append('order', '0');
                    const res = await api.post('/article-images/', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
                    setGallerySlots(prev => [...prev, { id: res.data.id, url: res.data.image.startsWith('http') ? res.data.image : `https://heroic-healing-production-2365.up.railway.app${res.data.image}` }]);
                }));
            } catch (err) {
                console.error('Failed to upload gallery image:', err);
            } finally {
                setUploadingGallery(false);
            }
        } else {
            // Stage for later (new article)
            Array.from(files).forEach(file => {
                setGallerySlots(prev => [...prev, { id: 0, url: URL.createObjectURL(file), file }]);
            });
        }
    };

    const removeGallerySlot = async (gi: number) => {
        const gs = gallerySlots[gi];
        if (gs.id > 0) {
            try { await api.delete(`/article-images/${gs.id}/`); } catch { /* 404 ok */ }
        }
        setGallerySlots(prev => prev.filter((_, i) => i !== gi));
    };

    const addFileInputRef = useCallback((el: HTMLInputElement | null, idx: number) => {
        fileInputRefs.current[idx] = el;
    }, []);

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100">
            {/* Header */}
            <div className="border-b border-gray-100 bg-gray-50/50 p-6 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-white rounded-lg shadow-sm">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-orange-500"><rect width="18" height="18" x="3" y="3" rx="2" ry="2" /><circle cx="9" cy="9" r="2" /><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" /></svg>
                    </div>
                    <div className="flex items-center gap-3">
                        <h2 className="text-lg font-semibold text-gray-900">Images</h2>
                        {imageSource && imageSource !== 'unknown' && (() => {
                            const cls: Record<string, string> = {
                                pexels: 'bg-purple-100 text-purple-700 border-purple-200',
                                youtube: 'bg-red-100 text-red-700 border-red-200',
                                rss_original: 'bg-blue-100 text-blue-700 border-blue-200',
                                uploaded: 'bg-green-100 text-green-700 border-green-200',
                                ai_generated: 'bg-amber-100 text-amber-700 border-amber-200',
                            };
                            const labels: Record<string, string> = {
                                pexels: '📷 Pexels Stock', youtube: '🎥 YouTube Thumbnail',
                                rss_original: '📰 Source: Press Release', uploaded: '📤 Manual Upload',
                                ai_generated: '🤖 AI Generated',
                            };
                            return (
                                <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${cls[imageSource] ?? 'bg-gray-100 text-gray-600 border-gray-200'}`}>
                                    {labels[imageSource] ?? imageSource}
                                </span>
                            );
                        })()}
                    </div>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-gray-400">
                    <ArrowLeftRight className="w-3 h-3" />
                    Drag to reorder
                </div>
            </div>

            <div className="p-6">
                <p className="text-sm text-gray-500 mb-4">
                    Drag cards to reorder or swap. Drop files to upload.
                    <span className="ml-2 text-gray-400">Slots 1-3 auto-embed in article · Slot 4+ go to Vehicle Gallery</span>
                </p>

                {/* Unified grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {Array.from({ length: totalCards }).map((_, cardIdx) => {
                        const card = getCardType(cardIdx);
                        const { label, sublabel } = getSlotLabel(cardIdx + 1);

                        // Determine preview URL + states
                        let currentImg = '';
                        let fileImg: File | null = null;
                        let isDeleted = false;

                        if (card.kind === 'main') {
                            currentImg = formData[card.currentKey] as string || '';
                            fileImg = formData[card.fileKey] as File | null;
                            isDeleted = formData[card.deleteKey] as boolean;
                        } else {
                            currentImg = card.gallerySlot.url;
                            fileImg = card.gallerySlot.file || null;
                            isDeleted = !!(card.gallerySlot.pendingDelete);
                        }

                        const hasImage = (!!currentImg && !isDeleted) || !!fileImg;
                        const isDragTarget = dragOver === cardIdx && dragSource !== null && dragSource !== cardIdx;
                        const isGallery = card.kind === 'gallery';

                        return (
                            <div
                                key={cardIdx}
                                className={`rounded-xl border-2 transition-all overflow-visible ${isDragTarget
                                    ? 'border-indigo-400 bg-indigo-50/30 scale-[1.02]'
                                    : dragOver === cardIdx
                                        ? 'border-blue-300 bg-blue-50/20'
                                        : isGallery
                                            ? 'border-teal-200 bg-teal-50/20'
                                            : 'border-gray-200 bg-gray-50/30'
                                    }`}
                                onDragOver={(e) => { e.preventDefault(); setDragOver(cardIdx); }}
                                onDragLeave={() => setDragOver(null)}
                                onDrop={(e) => {
                                    if (dragSource !== null && dragSource !== cardIdx) {
                                        e.preventDefault();
                                        swapCards(dragSource, cardIdx);
                                        setDragSource(null); setDragOver(null);
                                    } else {
                                        handleFileDrop(e, cardIdx);
                                    }
                                }}
                            >
                                {/* Card header */}
                                <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-200/70">
                                    <div
                                        className="cursor-grab active:cursor-grabbing p-1 rounded hover:bg-gray-200/50 transition-colors"
                                        draggable
                                        onDragStart={() => setDragSource(cardIdx)}
                                        onDragEnd={() => { setDragSource(null); setDragOver(null); }}
                                    >
                                        <GripVertical className="w-3.5 h-3.5 text-gray-400" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="text-xs font-semibold text-gray-700 truncate">{label}</div>
                                        <div className={`text-[10px] truncate ${isGallery ? 'text-teal-500' : 'text-gray-400'}`}>{sublabel}</div>
                                    </div>
                                    {isGallery && (
                                        <button
                                            type="button"
                                            onClick={() => removeGallerySlot(card.galleryIndex)}
                                            className="p-0.5 rounded hover:bg-red-100 transition-colors text-gray-400 hover:text-red-500 flex-shrink-0"
                                            title="Remove gallery image"
                                        >
                                            <X className="w-3.5 h-3.5" />
                                        </button>
                                    )}
                                </div>

                                <div className="p-3 space-y-2">
                                    {/* Current image preview */}
                                    {currentImg && !isDeleted && !fileImg && (
                                        <div
                                            className="relative h-48 rounded-lg overflow-hidden border border-gray-200 group cursor-pointer bg-gray-100"
                                            onClick={() => setPreviewImage(currentImg)}
                                        >
                                            {/* eslint-disable-next-line @next/next/no-img-element */}
                                            <img src={currentImg} alt={label} className="w-full h-full object-cover" />
                                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center">
                                                <Maximize2 className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" />
                                            </div>
                                            <div className="absolute top-1.5 right-1.5 flex gap-1">
                                                <span className="bg-green-500/90 text-white text-[10px] px-1.5 py-0.5 rounded shadow-sm font-medium">Current</span>
                                                <button
                                                    type="button"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        if (card.kind === 'main') {
                                                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                                            setFormData((prev: any) => ({ ...prev, [card.deleteKey]: true }));
                                                            onSlotChange?.(card.slot, currentImg || null, null);
                                                        } else {
                                                            removeGallerySlot(card.galleryIndex);
                                                        }
                                                    }}
                                                    className="bg-red-500/90 text-white text-[10px] px-1.5 py-0.5 rounded shadow-sm hover:bg-red-600 transition-colors font-medium"
                                                >
                                                    Remove
                                                </button>
                                            </div>
                                            <ImageMeta src={currentImg} />
                                        </div>
                                    )}

                                    {/* Marked for deletion */}
                                    {isDeleted && card.kind === 'main' && (
                                        <div className="text-xs text-red-600 bg-red-50 p-2 rounded-lg border border-red-200 flex justify-between items-center">
                                            <span>Marked for deletion</span>
                                            <button type="button"
                                                onClick={() => {
                                                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                                    setFormData((prev: any) => ({ ...prev, [card.deleteKey]: false }));
                                                    onSlotChange?.(card.slot, null, currentImg || null);
                                                }}
                                                className="text-gray-600 underline text-[10px] hover:text-gray-900">Undo</button>
                                        </div>
                                    )}

                                    {/* Staged upload preview */}
                                    {fileImg && (
                                        <div className="relative h-48 rounded-lg overflow-hidden border-2 border-green-300 bg-gray-100">
                                            {/* eslint-disable-next-line @next/next/no-img-element */}
                                            <img src={URL.createObjectURL(fileImg)} alt="Upload preview" className="w-full h-full object-cover" />
                                            <div className="absolute top-1.5 right-1.5 flex gap-1">
                                                <span className="bg-green-500/90 text-white text-[10px] px-1.5 py-0.5 rounded shadow-sm font-medium">📤 New</span>
                                                <button type="button"
                                                    onClick={() => {
                                                        if (card.kind === 'main') {
                                                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                                            setFormData((prev: any) => ({ ...prev, [card.fileKey]: null }));
                                                        } else {
                                                            setGallerySlots(prev => {
                                                                const updated = [...prev];
                                                                updated[card.galleryIndex] = { ...updated[card.galleryIndex], file: undefined };
                                                                return updated;
                                                            });
                                                        }
                                                    }}
                                                    className="bg-red-500/90 text-white text-[10px] px-1.5 py-0.5 rounded shadow-sm hover:bg-red-600 transition-colors font-medium">✕</button>
                                            </div>
                                            <div className="absolute bottom-1.5 left-1.5 text-[10px] text-white/80 font-mono bg-black/40 px-1.5 py-0.5 rounded">
                                                {(fileImg.size / 1024).toFixed(0)}KB
                                            </div>
                                        </div>
                                    )}

                                    {/* Empty drop zone */}
                                    {!currentImg && !fileImg && !isDeleted && (
                                        <div className="h-48 rounded-lg border-2 border-dashed border-gray-300 flex flex-col items-center justify-center text-gray-400 bg-gray-50/50 transition-colors hover:border-gray-400 hover:bg-gray-50">
                                            <Upload className="w-8 h-8 mb-2 opacity-40" />
                                            <span className="text-xs font-medium">Drop image here</span>
                                            <span className="text-[10px] mt-0.5">or use button below</span>
                                        </div>
                                    )}

                                    {/* Hidden file input (main slots) */}
                                    {card.kind === 'main' && (
                                        <input
                                            ref={el => addFileInputRef(el, cardIdx)}
                                            type="file" accept="image/*"
                                            onChange={(e) => {
                                                const file = e.target.files?.[0] || null;
                                                if (file) {
                                                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                                    setFormData((prev: any) => ({ ...prev, [card.fileKey]: file, [card.deleteKey]: false }));
                                                    if (card.slotIndex === 0) setImageSource('uploaded');
                                                }
                                            }}
                                            className="hidden"
                                        />
                                    )}

                                    {/* Action dropdown — only for main slots */}
                                    {card.kind === 'main' && (
                                        <SlotActions
                                            slot={card.slot}
                                            hasImage={hasImage}
                                            hasYoutubeUrl={!!formData.youtube_url}
                                            onUpload={() => fileInputRefs.current[cardIdx]?.click()}
                                            onFindPhoto={() => openPhotoSearch(card.slot)}
                                            onAIGenerate={(style, mode, prompt) => generateAIImage(card.slot, style, mode, prompt)}
                                            onYouTubeRestore={restoreYouTubeThumbnail}
                                            photoSearchLoading={photoSearchLoading}
                                            generatingAI={generatingAI}
                                            restoringYT={restoringYT}
                                            canGenerateAI={card.slotIndex === 0 ? !!(currentImg || fileImg) : !!formData.current_image}
                                        />
                                    )}

                                    {/* Upload button for gallery slots without image */}
                                    {card.kind === 'gallery' && !hasImage && (
                                        <label className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-teal-500 to-emerald-600 text-white rounded-lg hover:from-teal-600 hover:to-emerald-700 transition-all text-sm font-medium shadow-sm w-full justify-center cursor-pointer">
                                            <Upload className="w-3.5 h-3.5" /> Upload Image
                                            <input type="file" accept="image/*" className="hidden"
                                                onChange={(e) => {
                                                    const file = e.target.files?.[0];
                                                    if (file) placeFileInCard(cardIdx, file);
                                                }} />
                                        </label>
                                    )}

                                    {/* Gallery slot: replace button if has image */}
                                    {card.kind === 'gallery' && hasImage && (
                                        <label className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-teal-500 to-emerald-600 text-white rounded-lg hover:from-teal-600 hover:to-emerald-700 transition-all text-sm font-medium shadow-sm w-full justify-center cursor-pointer">
                                            <ImageIcon className="w-3.5 h-3.5" /> Replace <ChevronDown className="w-3.5 h-3.5" />
                                            <input type="file" accept="image/*" className="hidden"
                                                onChange={(e) => {
                                                    const file = e.target.files?.[0];
                                                    if (file) {
                                                        if (card.gallerySlot.id > 0 && articleId) {
                                                            // Delete old + upload new
                                                            api.delete(`/article-images/${card.gallerySlot.id}/`).catch(() => { });
                                                            const fd = new FormData();
                                                            fd.append('article', articleId);
                                                            fd.append('image', file);
                                                            fd.append('order', '0');
                                                            api.post('/article-images/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
                                                                .then(res => {
                                                                    setGallerySlots(prev => {
                                                                        const updated = [...prev];
                                                                        updated[card.galleryIndex] = { id: res.data.id, url: res.data.image.startsWith('http') ? res.data.image : `https://heroic-healing-production-2365.up.railway.app${res.data.image}` };
                                                                        return updated;
                                                                    });
                                                                })
                                                                .catch(() => { });
                                                        } else {
                                                            placeFileInCard(cardIdx, file);
                                                        }
                                                    }
                                                }} />
                                        </label>
                                    )}
                                </div>
                            </div>
                        );
                    })}

                    {/* "+ Add More" card — always last */}
                    <label className={`rounded-xl border-2 border-dashed flex flex-col items-center justify-center min-h-[280px] transition-all cursor-pointer ${uploadingGallery ? 'border-gray-200 bg-gray-50 opacity-60 cursor-wait' : 'border-teal-300 bg-teal-50/30 hover:border-teal-400 hover:bg-teal-50/50'}`}>
                        {uploadingGallery ? (
                            <><Loader2 className="w-8 h-8 text-teal-400 animate-spin mb-2" /><span className="text-xs text-teal-600 font-medium">Uploading...</span></>
                        ) : (
                            <><Plus className="w-8 h-8 text-teal-400 mb-2" /><span className="text-xs text-teal-600 font-semibold">Add More Images</span><span className="text-[10px] text-teal-400 mt-0.5">Goes to Gallery</span></>
                        )}
                        <input type="file" accept="image/*" multiple disabled={uploadingGallery} className="hidden"
                            onChange={(e) => addGallerySlot(e.target.files)} />
                    </label>
                </div>
            </div>
        </div>
    );
}
