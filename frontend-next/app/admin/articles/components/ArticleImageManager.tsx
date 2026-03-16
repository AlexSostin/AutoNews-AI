import React, { useCallback, useRef, useState } from 'react';
import { Loader2, Search, Wand2, Maximize2, Video, Upload, ChevronDown, GripVertical, ArrowLeftRight } from 'lucide-react';

/* ═══════════════════════════════════════════════════════════════════════
   ArticleImageManager — Redesigned with:
   1. Bigger previews (h-48)
   2. Consolidated action dropdowns
   3. AI style selection inside dropdown
   4. Drag-and-drop upload
   5. Resolution & file size display
   6. Descriptive slot labels
   7. Drag-to-reorder between slots
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
}

// ── Image metadata component ────────────────────────────────────────────
function ImageMeta({ src }: { src: string }) {
    const [meta, setMeta] = useState<{ w: number; h: number; size?: string } | null>(null);
    const imgRef = useRef<HTMLImageElement>(null);

    const handleLoad = useCallback(() => {
        const img = imgRef.current;
        if (img) {
            setMeta(prev => ({ ...prev, w: img.naturalWidth, h: img.naturalHeight, size: prev?.size }));
        }
    }, []);

    // Try to get file size via HEAD request (for remote images)
    React.useEffect(() => {
        if (!src || !src.startsWith('http')) return;
        const controller = new AbortController();
        fetch(src, { method: 'HEAD', signal: controller.signal })
            .then(res => {
                const len = res.headers.get('content-length');
                if (len) {
                    const kb = Math.round(parseInt(len) / 1024);
                    const sizeStr = kb > 1024 ? `${(kb / 1024).toFixed(1)}MB` : `${kb}KB`;
                    setMeta(prev => prev ? { ...prev, size: sizeStr } : { w: 0, h: 0, size: sizeStr });
                }
            })
            .catch(() => { /* ignore */ });
        return () => controller.abort();
    }, [src]);

    return (
        <>
            {/* Hidden img to get natural dimensions */}
            <img ref={imgRef} src={src} onLoad={handleLoad} alt="" className="hidden" />
            {meta && (meta.w > 0 || meta.size) && (
                <div className="text-[10px] text-gray-400 mt-1 font-mono">
                    {meta.w > 0 && `${meta.w}×${meta.h}`}
                    {meta.w > 0 && meta.size && ' • '}
                    {meta.size}
                </div>
            )}
        </>
    );
}

// ── Action dropdown for each slot ───────────────────────────────────────
function SlotActions({
    slot,
    hasImage,
    hasYoutubeUrl,
    onUpload,
    onFindPhoto,
    onAIGenerate,
    onYouTubeRestore,
    photoSearchLoading,
    generatingAI,
    restoringYT,
    canGenerateAI,
}: {
    slot: number;
    hasImage: boolean;
    hasYoutubeUrl: boolean;
    onUpload: () => void;
    onFindPhoto: () => void;
    onAIGenerate: (style: string, mode: 'auto' | 'custom', prompt: string) => void;
    onYouTubeRestore: () => void;
    photoSearchLoading: boolean;
    generatingAI: number | null;
    restoringYT: boolean;
    canGenerateAI: boolean;
}) {
    const [open, setOpen] = useState(false);
    const [showAI, setShowAI] = useState(false);
    const [aiMode, setAiMode] = useState<'auto' | 'custom'>('auto');
    const [aiStyle, setAiStyle] = useState('scenic_road');
    const [aiCustomPrompt, setAiCustomPrompt] = useState('');
    const dropdownRef = useRef<HTMLDivElement>(null);

    const aiStyles = [
        { key: 'scenic_road', label: '🏔️ Scenic Road' },
        { key: 'desert_sunset', label: '🌅 Desert Sunset' },
        { key: 'urban_city', label: '🌃 Urban City' },
        { key: 'mountain_pass', label: '⛰️ Mountain Pass' },
        { key: 'studio', label: '📸 Studio' },
        { key: 'coastal', label: '🌊 Coastal' },
        { key: 'forest', label: '🌲 Forest' },
        { key: 'showroom', label: '✨ Showroom' },
    ];

    // Close dropdown on outside click
    React.useEffect(() => {
        if (!open) return;
        const handler = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setOpen(false);
                setShowAI(false);
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
                {isLoading ? (
                    <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Working...</>
                ) : (
                    <>{hasImage ? 'Replace' : 'Add Image'} <ChevronDown className="w-3.5 h-3.5" /></>
                )}
            </button>

            {open && (
                <div className="absolute z-30 top-full mt-1 left-0 right-0 bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden min-w-[220px]">
                    {/* Upload */}
                    <label className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-gray-50 cursor-pointer transition-colors text-sm text-gray-700">
                        <Upload className="w-4 h-4 text-gray-500" />
                        <span>📁 Upload from device</span>
                        <input type="file" accept="image/*" onChange={() => { onUpload(); setOpen(false); }} className="hidden" />
                    </label>

                    {/* Find Photo */}
                    <button
                        type="button"
                        onClick={() => { onFindPhoto(); setOpen(false); }}
                        disabled={photoSearchLoading}
                        className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-gray-50 transition-colors text-sm text-gray-700 w-full text-left disabled:opacity-50"
                    >
                        <Search className="w-4 h-4 text-emerald-500" />
                        <span>🔍 Find Photo (Pexels)</span>
                    </button>

                    {/* AI Generate */}
                    <button
                        type="button"
                        onClick={() => setShowAI(!showAI)}
                        disabled={!canGenerateAI || generatingAI !== null}
                        className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-gray-50 transition-colors text-sm text-gray-700 w-full text-left disabled:opacity-50"
                    >
                        <Wand2 className="w-4 h-4 text-purple-500" />
                        <span>🎨 AI Generate</span>
                        {!canGenerateAI && <span className="text-[10px] text-gray-400 ml-auto">needs img</span>}
                    </button>

                    {/* AI submenu */}
                    {showAI && canGenerateAI && (
                        <div className="border-t border-gray-100 bg-purple-50/50 px-4 py-3 space-y-2">
                            <div className="flex gap-1">
                                <button type="button" onClick={() => setAiMode('auto')} className={`px-2.5 py-1 text-xs font-bold rounded-l-lg border ${aiMode === 'auto' ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-purple-600 border-purple-300'}`}>
                                    🚗 Auto
                                </button>
                                <button type="button" onClick={() => setAiMode('custom')} className={`px-2.5 py-1 text-xs font-bold rounded-r-lg border-t border-b border-r ${aiMode === 'custom' ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-purple-600 border-purple-300'}`}>
                                    ✏️ Custom
                                </button>
                            </div>
                            {aiMode === 'auto' && (
                                <select value={aiStyle} onChange={(e) => setAiStyle(e.target.value)} className="w-full px-2 py-1.5 text-xs border border-purple-300 rounded-lg bg-white text-gray-800 outline-none">
                                    {aiStyles.map(s => <option key={s.key} value={s.key}>{s.label}</option>)}
                                </select>
                            )}
                            {aiMode === 'custom' && (
                                <input type="text" value={aiCustomPrompt} onChange={(e) => setAiCustomPrompt(e.target.value)} placeholder="Describe the image..." className="w-full px-2 py-1.5 text-xs border border-purple-300 rounded-lg bg-white text-gray-800 outline-none placeholder:text-gray-400" />
                            )}
                            <button
                                type="button"
                                onClick={() => { onAIGenerate(aiStyle, aiMode, aiCustomPrompt); setOpen(false); setShowAI(false); }}
                                className="w-full px-3 py-1.5 bg-purple-600 text-white rounded-lg text-xs font-bold hover:bg-purple-700 transition-colors"
                            >
                                {generatingAI === slot ? 'Generating...' : '✨ Generate'}
                            </button>
                        </div>
                    )}

                    {/* YouTube Restore (slot 1 only) */}
                    {slot === 1 && hasYoutubeUrl && (
                        <button
                            type="button"
                            onClick={() => { onYouTubeRestore(); setOpen(false); }}
                            disabled={restoringYT || generatingAI !== null}
                            className="flex items-center gap-2.5 px-4 py-2.5 hover:bg-gray-50 transition-colors text-sm text-gray-700 w-full text-left disabled:opacity-50 border-t border-gray-100"
                        >
                            <Video className="w-4 h-4 text-red-500" />
                            <span>🎥 YouTube Thumbnail</span>
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}

// ── Main component ──────────────────────────────────────────────────────
export function ArticleImageManager({
    formData,
    setFormData,
    imageSource,
    setImageSource,
    setPreviewImage,
    openPhotoSearch,
    photoSearchLoading,
    generateAIImage,
    generatingAI,
    restoreYouTubeThumbnail,
    restoringYT,
}: ArticleImageManagerProps) {

    const [dragSource, setDragSource] = useState<number | null>(null);
    const [dragOver, setDragOver] = useState<number | null>(null);
    const fileInputRefs = useRef<(HTMLInputElement | null)[]>([null, null, null]);

    // Slot config
    const slots = [
        { slot: 1, label: 'Image 1 — Cover', sublabel: 'Main article thumbnail', currentKey: 'current_image', fileKey: 'image', deleteKey: 'delete_image' },
        { slot: 2, label: 'Image 2 — Body Inline', sublabel: 'Auto-inserted between sections', currentKey: 'current_image_2', fileKey: 'image_2', deleteKey: 'delete_image_2' },
        { slot: 3, label: 'Image 3 — Body Inline', sublabel: 'Auto-inserted between sections', currentKey: 'current_image_3', fileKey: 'image_3', deleteKey: 'delete_image_3' },
    ];

    // Reorder: swap two image slots
    const swapSlots = (a: number, b: number) => {
        if (a === b) return;
        const slotA = slots[a];
        const slotB = slots[b];
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setFormData((prev: any) => ({
            ...prev,
            [slotA.currentKey]: prev[slotB.currentKey],
            [slotA.fileKey]: prev[slotB.fileKey],
            [slotA.deleteKey]: prev[slotB.deleteKey],
            [slotB.currentKey]: prev[slotA.currentKey],
            [slotB.fileKey]: prev[slotA.fileKey],
            [slotB.deleteKey]: prev[slotA.deleteKey],
        }));
    };

    // Drag-and-drop file upload handler
    const handleFileDrop = (e: React.DragEvent, slotIndex: number) => {
        e.preventDefault();
        setDragOver(null);
        const file = e.dataTransfer.files?.[0];
        if (!file || !file.type.startsWith('image/')) return;
        const slot = slots[slotIndex];
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setFormData((prev: any) => ({
            ...prev,
            [slot.fileKey]: file,
            [slot.deleteKey]: false,
        }));
        if (slotIndex === 0) setImageSource('uploaded');
    };

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="border-b border-gray-100 bg-gray-50/50 p-6 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-white rounded-lg shadow-sm">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-orange-500"><rect width="18" height="18" x="3" y="3" rx="2" ry="2" /><circle cx="9" cy="9" r="2" /><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" /></svg>
                    </div>
                    <div className="flex items-center gap-3">
                        <h2 className="text-lg font-semibold text-gray-900">Images</h2>
                        {imageSource && imageSource !== 'unknown' && (
                            <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${imageSource === 'pexels' ? 'bg-purple-100 text-purple-700 border border-purple-200' :
                                imageSource === 'youtube' ? 'bg-red-100 text-red-700 border border-red-200' :
                                    imageSource === 'rss_original' ? 'bg-blue-100 text-blue-700 border border-blue-200' :
                                        imageSource === 'uploaded' ? 'bg-green-100 text-green-700 border border-green-200' :
                                            imageSource === 'ai_generated' ? 'bg-amber-100 text-amber-700 border border-amber-200' :
                                                'bg-gray-100 text-gray-600 border border-gray-200'
                                }`}>
                                {imageSource === 'pexels' && '📷 Pexels Stock'}
                                {imageSource === 'youtube' && '🎥 YouTube Thumbnail'}
                                {imageSource === 'rss_original' && '📰 Source: Press Release'}
                                {imageSource === 'uploaded' && '📤 Manual Upload'}
                                {imageSource === 'ai_generated' && '🤖 AI Generated'}
                            </span>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-gray-400">
                    <ArrowLeftRight className="w-3 h-3" />
                    Drag to reorder
                </div>
            </div>
            <div className="p-6">
                <p className="text-sm text-gray-500 mb-4">Drag images between slots to reorder. Drop files onto any card to upload.</p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {slots.map((s, idx) => {
                        const currentImg = formData[s.currentKey] as string;
                        const fileImg = formData[s.fileKey] as File | null;
                        const isDeleted = formData[s.deleteKey] as boolean;
                        const hasImage = (!!currentImg && !isDeleted) || !!fileImg;
                        const isDragTarget = dragOver === idx && dragSource !== null && dragSource !== idx;

                        return (
                            <div
                                key={s.slot}
                                className={`rounded-xl border-2 transition-all ${isDragTarget
                                    ? 'border-indigo-400 bg-indigo-50/30 scale-[1.02]'
                                    : dragOver === idx
                                        ? 'border-blue-300 bg-blue-50/20'
                                        : 'border-gray-200 bg-gray-50/30'
                                    }`}
                                onDragOver={(e) => { e.preventDefault(); setDragOver(idx); }}
                                onDragLeave={() => setDragOver(null)}
                                onDrop={(e) => {
                                    // If it's a slot reorder (internal drag)
                                    if (dragSource !== null && dragSource !== idx) {
                                        e.preventDefault();
                                        swapSlots(dragSource, idx);
                                        setDragSource(null);
                                        setDragOver(null);
                                    } else {
                                        // File drop
                                        handleFileDrop(e, idx);
                                    }
                                }}
                            >
                                {/* Header with drag handle */}
                                <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-200/70">
                                    <div
                                        className="cursor-grab active:cursor-grabbing p-1 rounded hover:bg-gray-200/50 transition-colors"
                                        draggable
                                        onDragStart={() => setDragSource(idx)}
                                        onDragEnd={() => { setDragSource(null); setDragOver(null); }}
                                    >
                                        <GripVertical className="w-3.5 h-3.5 text-gray-400" />
                                    </div>
                                    <div>
                                        <div className="text-xs font-semibold text-gray-700">{s.label}</div>
                                        <div className="text-[10px] text-gray-400">{s.sublabel}</div>
                                    </div>
                                </div>

                                <div className="p-3 space-y-2">
                                    {/* Preview area */}
                                    {currentImg && !isDeleted && (
                                        <div
                                            className="relative h-48 rounded-lg overflow-hidden border border-gray-200 group cursor-pointer bg-gray-100"
                                            onClick={() => setPreviewImage(currentImg)}
                                        >
                                            {/* eslint-disable-next-line @next/next/no-img-element */}
                                            <img src={currentImg} alt={`Image ${s.slot}`} className="w-full h-full object-cover" />
                                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center">
                                                <Maximize2 className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" />
                                            </div>
                                            <div className="absolute top-1.5 right-1.5 flex gap-1">
                                                <span className="bg-green-500/90 text-white text-[10px] px-1.5 py-0.5 rounded shadow-sm font-medium">Current</span>
                                                <button
                                                    type="button"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                                        setFormData((prev: any) => ({ ...prev, [s.deleteKey]: true }));
                                                    }}
                                                    className="bg-red-500/90 text-white text-[10px] px-1.5 py-0.5 rounded shadow-sm hover:bg-red-600 transition-colors font-medium"
                                                >
                                                    Remove
                                                </button>
                                            </div>
                                            <ImageMeta src={currentImg} />
                                        </div>
                                    )}

                                    {isDeleted && (
                                        <div className="text-xs text-red-600 bg-red-50 p-2 rounded-lg border border-red-200 flex justify-between items-center">
                                            <span>Marked for deletion</span>
                                            <button
                                                type="button"
                                                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                                onClick={() => setFormData((prev: any) => ({ ...prev, [s.deleteKey]: false }))}
                                                className="text-gray-600 underline text-[10px] hover:text-gray-900"
                                            >
                                                Undo
                                            </button>
                                        </div>
                                    )}

                                    {/* New upload preview */}
                                    {fileImg && (
                                        <div className="relative h-48 rounded-lg overflow-hidden border-2 border-green-300 bg-gray-100">
                                            {/* eslint-disable-next-line @next/next/no-img-element */}
                                            <img src={URL.createObjectURL(fileImg)} alt="Upload preview" className="w-full h-full object-cover" />
                                            <span className="absolute top-1.5 right-1.5 bg-green-500/90 text-white text-[10px] px-1.5 py-0.5 rounded shadow-sm font-medium">📤 New</span>
                                            <div className="absolute bottom-1.5 left-1.5 text-[10px] text-white/80 font-mono bg-black/40 px-1.5 py-0.5 rounded">
                                                {(fileImg.size / 1024).toFixed(0)}KB
                                            </div>
                                        </div>
                                    )}

                                    {/* Empty state with drop zone */}
                                    {!currentImg && !fileImg && !isDeleted && (
                                        <div className="h-48 rounded-lg border-2 border-dashed border-gray-300 flex flex-col items-center justify-center text-gray-400 bg-gray-50/50 transition-colors hover:border-gray-400 hover:bg-gray-50">
                                            <Upload className="w-8 h-8 mb-2 opacity-40" />
                                            <span className="text-xs font-medium">Drop image here</span>
                                            <span className="text-[10px] mt-0.5">or use button below</span>
                                        </div>
                                    )}

                                    {/* Hidden file input */}
                                    <input
                                        ref={el => { fileInputRefs.current[idx] = el; }}
                                        type="file"
                                        accept="image/*"
                                        onChange={(e) => {
                                            const file = e.target.files?.[0] || null;
                                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                            setFormData((prev: any) => ({ ...prev, [s.fileKey]: file, [s.deleteKey]: false }));
                                            if (idx === 0 && file) setImageSource('uploaded');
                                        }}
                                        className="hidden"
                                    />

                                    {/* Action dropdown */}
                                    <SlotActions
                                        slot={s.slot}
                                        hasImage={hasImage}
                                        hasYoutubeUrl={!!formData.youtube_url}
                                        onUpload={() => fileInputRefs.current[idx]?.click()}
                                        onFindPhoto={() => openPhotoSearch(s.slot)}
                                        onAIGenerate={(style, mode, prompt) => generateAIImage(s.slot, style, mode, prompt)}
                                        onYouTubeRestore={restoreYouTubeThumbnail}
                                        photoSearchLoading={photoSearchLoading}
                                        generatingAI={generatingAI}
                                        restoringYT={restoringYT}
                                        canGenerateAI={idx === 0 ? !!(currentImg || fileImg) : !!formData.current_image}
                                    />
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
