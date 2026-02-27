import React from 'react';
import { Loader2, Search, Wand2, Maximize2 } from 'lucide-react';

interface ArticleImageManagerProps {
    formData: any;
    setFormData: (data: any) => void;
    imageSource: string;
    setImageSource: (source: string) => void;
    setPreviewImage: (url: string | null) => void;
    openPhotoSearch: (slot: number) => void;
    photoSearchLoading: boolean;
    generateAIImage: (slot: number, style: string, mode: 'auto' | 'custom', customPrompt: string) => Promise<void>;
    generatingAI: number | null;
}

export function ArticleImageManager({
    formData,
    setFormData,
    imageSource,
    setImageSource,
    setPreviewImage,
    openPhotoSearch,
    photoSearchLoading,
    generateAIImage,
    generatingAI
}: ArticleImageManagerProps) {
    const [aiMode, setAiMode] = React.useState<'auto' | 'custom'>('auto');
    const [aiStyle, setAiStyle] = React.useState('scenic_road');
    const [aiCustomPrompt, setAiCustomPrompt] = React.useState('');

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
                                {imageSource === 'rss_original' && `📰 Source: Press Release`}
                                {imageSource === 'uploaded' && '📤 Manual Upload'}
                                {imageSource === 'ai_generated' && '🤖 AI Generated'}
                            </span>
                        )}
                    </div>
                </div>
            </div>
            <div className="p-6">
                <p className="text-sm text-gray-500 mb-4">Replace images or keep existing ones from AI generation</p>

                {/* AI Image Generation Mode */}
                <div className="mb-4 p-3 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-200">
                    <div className="flex items-center gap-1 mb-3">
                        <Wand2 className="w-4 h-4 text-purple-700" />
                        <span className="text-sm font-semibold text-purple-800 mr-2">AI Photo:</span>
                        <button
                            type="button"
                            onClick={() => setAiMode('auto')}
                            className={`px-3 py-1 text-xs font-bold rounded-l-lg border transition-all ${aiMode === 'auto'
                                ? 'bg-purple-600 text-white border-purple-600 shadow-sm'
                                : 'bg-white text-purple-600 border-purple-300 hover:bg-purple-50'
                                }`}
                        >
                            🚗 Auto
                        </button>
                        <button
                            type="button"
                            onClick={() => setAiMode('custom')}
                            className={`px-3 py-1 text-xs font-bold rounded-r-lg border-t border-b border-r transition-all ${aiMode === 'custom'
                                ? 'bg-purple-600 text-white border-purple-600 shadow-sm'
                                : 'bg-white text-purple-600 border-purple-300 hover:bg-purple-50'
                                }`}
                        >
                            ✏️ Custom
                        </button>
                    </div>

                    {aiMode === 'auto' && (
                        <div className="flex items-center gap-3 flex-wrap">
                            <select
                                value={aiStyle}
                                onChange={(e) => setAiStyle(e.target.value)}
                                className="px-3 py-1.5 text-sm border border-purple-300 rounded-lg bg-white text-gray-800 focus:ring-2 focus:ring-purple-400 focus:border-transparent outline-none"
                            >
                                {aiStyles.map(s => (
                                    <option key={s.key} value={s.key}>{s.label}</option>
                                ))}
                            </select>
                            <span className="text-xs text-purple-600">AI generates a car photo with the selected scene style</span>
                        </div>
                    )}

                    {aiMode === 'custom' && (
                        <div>
                            <input
                                type="text"
                                value={aiCustomPrompt}
                                onChange={(e) => setAiCustomPrompt(e.target.value)}
                                placeholder="e.g. Futuristic steering yoke in a car cockpit, close-up, ambient blue lighting..."
                                className="w-full px-3 py-2 text-sm border border-purple-300 rounded-lg bg-white text-gray-800 focus:ring-2 focus:ring-purple-400 focus:border-transparent outline-none placeholder:text-gray-400"
                            />
                            <span className="text-[10px] text-purple-500 mt-1 block">Describe what you want — AI will generate any image using the reference photo as context</span>
                        </div>
                    )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Image 1 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Image 1 (Main)</label>
                        {formData.current_image && !formData.delete_image && (
                            <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200 group cursor-pointer" onClick={() => setPreviewImage(formData.current_image)}>
                                <img src={formData.current_image} alt="Current Image 1" className="w-full h-full object-cover" />
                                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center">
                                    <Maximize2 className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" />
                                </div>
                                <div className="absolute top-1 right-1 flex gap-1">
                                    <span className="bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">Current</span>
                                    <button type="button" onClick={(e) => { e.stopPropagation(); setFormData({ ...formData, delete_image: true }); }} className="bg-red-500 text-white text-xs px-2 py-1 rounded shadow-sm hover:bg-red-600 transition-colors">Remove</button>
                                </div>
                            </div>
                        )}
                        {formData.delete_image && (
                            <div className="mb-2 text-sm text-red-600 bg-red-50 p-2 rounded border border-red-200 flex justify-between items-center">
                                <span>Marked for deletion</span>
                                <button type="button" onClick={() => setFormData({ ...formData, delete_image: false })} className="text-gray-600 underline text-xs hover:text-gray-900">Undo</button>
                            </div>
                        )}
                        <label className="inline-flex items-center gap-2 px-3 py-2 bg-gray-50 text-gray-700 rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors cursor-pointer text-sm font-medium">
                            📁 {formData.current_image && !formData.delete_image ? 'Replace Image' : 'Choose Image'}
                            <input type="file" accept="image/*" onChange={(e) => { const file = e.target.files?.[0] || null; setFormData({ ...formData, image: file, delete_image: false }); setImageSource('uploaded'); }} className="hidden" />
                        </label>
                        {formData.image && (
                            <div className="mt-2 relative h-32 rounded-lg overflow-hidden border-2 border-green-300 bg-gray-100">
                                <img src={URL.createObjectURL(formData.image)} alt="Upload preview" className="w-full h-full object-cover" />
                                <span className="absolute top-1 right-1 bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">📤 New Upload</span>
                            </div>
                        )}
                        <div className="flex gap-1.5 mt-1">
                            <button type="button" onClick={() => openPhotoSearch(1)} disabled={photoSearchLoading} className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-lg hover:from-emerald-600 hover:to-teal-700 transition-all text-sm font-medium disabled:opacity-50 shadow-sm">
                                <Search className="w-3.5 h-3.5" /> 🔍 Find Photo
                            </button>
                            <button type="button" onClick={() => generateAIImage(1, aiStyle, aiMode, aiCustomPrompt)} disabled={generatingAI !== null || (!formData.current_image && !formData.image)} className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-lg hover:from-purple-600 hover:to-indigo-700 transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-sm">
                                {generatingAI === 1 ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</> : <><Wand2 className="w-3.5 h-3.5" /> 🎨 AI Photo</>}
                            </button>
                        </div>
                    </div>

                    {/* Image 2 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Image 2</label>
                        {formData.current_image_2 && !formData.delete_image_2 && (
                            <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200 group cursor-pointer" onClick={() => setPreviewImage(formData.current_image_2)}>
                                <img src={formData.current_image_2} alt="Current Image 2" className="w-full h-full object-cover" />
                                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center">
                                    <Maximize2 className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" />
                                </div>
                                <div className="absolute top-1 right-1 flex gap-1">
                                    <span className="bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">Current</span>
                                    <button type="button" onClick={(e) => { e.stopPropagation(); setFormData({ ...formData, delete_image_2: true }); }} className="bg-red-500 text-white text-xs px-2 py-1 rounded shadow-sm hover:bg-red-600 transition-colors">Remove</button>
                                </div>
                            </div>
                        )}
                        {formData.delete_image_2 && (
                            <div className="mb-2 text-sm text-red-600 bg-red-50 p-2 rounded border border-red-200 flex justify-between items-center">
                                <span>Marked for deletion</span>
                                <button type="button" onClick={() => setFormData({ ...formData, delete_image_2: false })} className="text-gray-600 underline text-xs hover:text-gray-900">Undo</button>
                            </div>
                        )}
                        <label className="inline-flex items-center gap-2 px-3 py-2 bg-gray-50 text-gray-700 rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors cursor-pointer text-sm font-medium">
                            📁 {formData.current_image_2 && !formData.delete_image_2 ? 'Replace Image' : 'Choose Image'}
                            <input type="file" accept="image/*" onChange={(e) => { setFormData({ ...formData, image_2: e.target.files?.[0] || null, delete_image_2: false }); }} className="hidden" />
                        </label>
                        {formData.image_2 && (
                            <div className="mt-2 relative h-32 rounded-lg overflow-hidden border-2 border-green-300 bg-gray-100">
                                <img src={URL.createObjectURL(formData.image_2)} alt="Upload preview" className="w-full h-full object-cover" />
                                <span className="absolute top-1 right-1 bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">📤 New Upload</span>
                            </div>
                        )}
                        <div className="flex gap-1.5 mt-1">
                            <button type="button" onClick={() => openPhotoSearch(2)} disabled={photoSearchLoading} className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-lg hover:from-emerald-600 hover:to-teal-700 transition-all text-sm font-medium disabled:opacity-50 shadow-sm">
                                <Search className="w-3.5 h-3.5" /> 🔍 Find Photo
                            </button>
                            <button type="button" onClick={() => generateAIImage(2, aiStyle, aiMode, aiCustomPrompt)} disabled={generatingAI !== null || !formData.current_image} className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-lg hover:from-purple-600 hover:to-indigo-700 transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-sm">
                                {generatingAI === 2 ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</> : <><Wand2 className="w-3.5 h-3.5" /> 🎨 AI Photo</>}
                            </button>
                        </div>
                    </div>

                    {/* Image 3 */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Image 3</label>
                        {formData.current_image_3 && !formData.delete_image_3 && (
                            <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200 group cursor-pointer" onClick={() => setPreviewImage(formData.current_image_3)}>
                                <img src={formData.current_image_3} alt="Current Image 3" className="w-full h-full object-cover" />
                                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-all flex items-center justify-center">
                                    <Maximize2 className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" />
                                </div>
                                <div className="absolute top-1 right-1 flex gap-1">
                                    <span className="bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">Current</span>
                                    <button type="button" onClick={(e) => { e.stopPropagation(); setFormData({ ...formData, delete_image_3: true }); }} className="bg-red-500 text-white text-xs px-2 py-1 rounded shadow-sm hover:bg-red-600 transition-colors">Remove</button>
                                </div>
                            </div>
                        )}
                        {formData.delete_image_3 && (
                            <div className="mb-2 text-sm text-red-600 bg-red-50 p-2 rounded border border-red-200 flex justify-between items-center">
                                <span>Marked for deletion</span>
                                <button type="button" onClick={() => setFormData({ ...formData, delete_image_3: false })} className="text-gray-600 underline text-xs hover:text-gray-900">Undo</button>
                            </div>
                        )}
                        <label className="inline-flex items-center gap-2 px-3 py-2 bg-gray-50 text-gray-700 rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors cursor-pointer text-sm font-medium">
                            📁 {formData.current_image_3 && !formData.delete_image_3 ? 'Replace Image' : 'Choose Image'}
                            <input type="file" accept="image/*" onChange={(e) => { setFormData({ ...formData, image_3: e.target.files?.[0] || null, delete_image_3: false }); }} className="hidden" />
                        </label>
                        {formData.image_3 && (
                            <div className="mt-2 relative h-32 rounded-lg overflow-hidden border-2 border-green-300 bg-gray-100">
                                <img src={URL.createObjectURL(formData.image_3)} alt="Upload preview" className="w-full h-full object-cover" />
                                <span className="absolute top-1 right-1 bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">📤 New Upload</span>
                            </div>
                        )}
                        <div className="flex gap-1.5 mt-1">
                            <button type="button" onClick={() => openPhotoSearch(3)} disabled={photoSearchLoading} className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-lg hover:from-emerald-600 hover:to-teal-700 transition-all text-sm font-medium disabled:opacity-50 shadow-sm">
                                <Search className="w-3.5 h-3.5" /> 🔍 Find Photo
                            </button>
                            <button type="button" onClick={() => generateAIImage(3, aiStyle, aiMode, aiCustomPrompt)} disabled={generatingAI !== null || !formData.current_image} className="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-lg hover:from-purple-600 hover:to-indigo-700 transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-sm">
                                {generatingAI === 3 ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</> : <><Wand2 className="w-3.5 h-3.5" /> 🎨 AI Photo</>}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
