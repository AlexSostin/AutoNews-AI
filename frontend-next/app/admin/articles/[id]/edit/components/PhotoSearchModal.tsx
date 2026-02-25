import { Loader2, Search, X, Download } from 'lucide-react';

interface PhotoSearchModalProps {
    photoSearchOpen: boolean;
    setPhotoSearchOpen: (open: boolean) => void;
    photoSearchSlot: number;
    photoSearchQuery: string;
    setPhotoSearchQuery: (query: string) => void;
    searchPhotosCustom: () => void;
    photoSearchLoading: boolean;
    photoSearchResults: any[];
    savingPhoto: string | null;
    selectPhoto: (url: string) => void;
}

export function PhotoSearchModal({
    photoSearchOpen,
    setPhotoSearchOpen,
    photoSearchSlot,
    photoSearchQuery,
    setPhotoSearchQuery,
    searchPhotosCustom,
    photoSearchLoading,
    photoSearchResults,
    savingPhoto,
    selectPhoto,
}: PhotoSearchModalProps) {
    if (!photoSearchOpen) return null;

    return (
        <div
            className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
            onClick={() => setPhotoSearchOpen(false)}
        >
            <div
                className="relative bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b bg-gradient-to-r from-emerald-50 to-teal-50">
                    <div>
                        <h3 className="text-lg font-bold text-gray-900">🔍 Find Press Photo</h3>
                        <p className="text-sm text-gray-500">Image Slot {photoSearchSlot} — select a photo to save</p>
                    </div>
                    <button
                        onClick={() => setPhotoSearchOpen(false)}
                        className="p-2 hover:bg-gray-200 rounded-full transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Search Bar */}
                <div className="px-6 py-3 border-b bg-gray-50">
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={photoSearchQuery}
                            onChange={(e) => setPhotoSearchQuery(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && searchPhotosCustom()}
                            placeholder="Search for car photos..."
                            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm text-gray-900"
                        />
                        <button
                            onClick={searchPhotosCustom}
                            disabled={photoSearchLoading}
                            className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-sm font-medium disabled:opacity-50"
                        >
                            {photoSearchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
                        </button>
                    </div>
                </div>

                {/* Results Grid */}
                <div className="flex-1 overflow-y-auto p-6">
                    {photoSearchLoading && photoSearchResults.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-16 text-gray-500">
                            <Loader2 className="w-10 h-10 animate-spin text-emerald-500 mb-3" />
                            <p className="text-sm font-medium">Searching for photos...</p>
                        </div>
                    ) : photoSearchResults.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-16 text-gray-400">
                            <Search className="w-10 h-10 mb-3" />
                            <p className="text-sm font-medium">No photos found. Try a different search query.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                            {photoSearchResults.map((photo, index) => (
                                <div
                                    key={index}
                                    className={`group relative rounded-xl overflow-hidden border-2 transition-all cursor-pointer hover:shadow-lg ${savingPhoto === photo.url
                                        ? 'border-emerald-500 ring-2 ring-emerald-200'
                                        : 'border-gray-200 hover:border-emerald-400'
                                        }`}
                                    onClick={() => !savingPhoto && selectPhoto(photo.url)}
                                >
                                    <div className="aspect-[4/3] bg-gray-100">
                                        <img
                                            src={photo.thumbnail}
                                            alt={photo.title}
                                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                            loading="lazy"
                                            onError={(e) => {
                                                (e.target as HTMLImageElement).style.display = 'none';
                                            }}
                                        />
                                    </div>
                                    {/* Overlay on hover */}
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-3">
                                        <p className="text-white text-xs font-medium line-clamp-2">{photo.title}</p>
                                        <p className="text-white/70 text-[10px] mt-0.5">{photo.source}</p>
                                        {photo.width > 0 && (
                                            <p className="text-white/50 text-[10px]">{photo.width}×{photo.height}</p>
                                        )}
                                    </div>
                                    {/* License badge */}
                                    {photo.license === 'editorial' && (
                                        <span className="absolute top-2 left-2 bg-emerald-500 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold shadow" title="From press/manufacturer site — safe for editorial use">
                                            ✅ EDITORIAL
                                        </span>
                                    )}
                                    {photo.license === 'cc' && (
                                        <span className="absolute top-2 left-2 bg-blue-500 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold shadow" title="Creative Commons — free to use with attribution">
                                            🆓 CC
                                        </span>
                                    )}
                                    {photo.license === 'unknown' && (
                                        <span className="absolute top-2 left-2 bg-amber-500 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold shadow" title="Unknown license — verify before commercial use">
                                            ⚠️ CHECK
                                        </span>
                                    )}
                                    {/* Download button */}
                                    <a
                                        href={photo.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        onClick={(e) => e.stopPropagation()}
                                        download
                                        className="absolute top-2 right-2 p-1.5 bg-black/60 hover:bg-black/80 text-white rounded-lg opacity-0 group-hover:opacity-100 transition-opacity shadow-lg"
                                        title="Open full-res image (right-click → Save As)"
                                    >
                                        <Download className="w-4 h-4" />
                                    </a>
                                    {/* Saving spinner */}
                                    {savingPhoto === photo.url && (
                                        <div className="absolute inset-0 bg-white/80 flex items-center justify-center">
                                            <div className="flex flex-col items-center">
                                                <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
                                                <p className="text-xs font-medium text-emerald-700 mt-1">Saving...</p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                {photoSearchResults.length > 0 && (
                    <div className="px-6 py-3 border-t bg-gray-50 text-xs text-gray-500">
                        <div className="flex justify-between items-center">
                            <span>{photoSearchResults.length} photos found — click to save, ⬇ to download</span>
                            <span>Image Slot {photoSearchSlot}</span>
                        </div>
                        <div className="flex gap-4 mt-1.5 text-[10px]">
                            <span><span className="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1" />EDITORIAL — press/manufacturer, safe for reviews</span>
                            <span><span className="inline-block w-2 h-2 rounded-full bg-blue-500 mr-1" />CC — Creative Commons, free with attribution</span>
                            <span><span className="inline-block w-2 h-2 rounded-full bg-amber-500 mr-1" />CHECK — verify license before publishing</span>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
