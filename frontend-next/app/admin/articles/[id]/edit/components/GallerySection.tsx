import { Plus, ArrowUp } from 'lucide-react';
import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';

export interface GalleryImage {
    id: number;
    image: string;
    caption: string;
    order: number;
}

export interface GallerySectionRef {
    upload: () => Promise<void>;
}

export interface AvailableSlot {
    slot: number;
    label: string;
}

interface GallerySectionProps {
    articleId: string | null;
    availableMainSlots?: AvailableSlot[];
    onPromoteToSlot?: (imageUrl: string, targetSlot: number, galleryImageId: number) => void;
    onGalleryLoaded?: (images: GalleryImage[]) => void;
}

export function GallerySection({ articleId, availableMainSlots, onPromoteToSlot, onGalleryLoaded }: GallerySectionProps) {
    const [galleryImages, setGalleryImages] = useState<GalleryImage[]>([]);
    const [uploadingGallery, setUploadingGallery] = useState(false);

    const fetchGalleryImages = useCallback(async (id: string) => {
        try {
            const response = await api.get(`/article-images/?article=${id}`);
            const images = response.data.results || response.data || [];
            setGalleryImages(images);
            onGalleryLoaded?.(images);
        } catch (error) {
            console.error('Failed to fetch gallery images:', error);
        }
    }, [onGalleryLoaded]);

    useEffect(() => {
        if (articleId) {
            fetchGalleryImages(articleId);
        }
    }, [articleId, fetchGalleryImages]);

    const deleteGalleryImage = async (imageId: number) => {
        if (!confirm('Delete this gallery image?')) return;
        try {
            await api.delete(`/article-images/${imageId}/`);
        } catch (error: unknown) {
            const status = (error as { response?: { status?: number } })?.response?.status;
            if (status !== 404) {
                console.error('Failed to delete gallery image:', error);
                alert('Failed to delete image');
                return;
            }
        }
        const updated = galleryImages.filter(img => img.id !== imageId);
        setGalleryImages(updated);
        onGalleryLoaded?.(updated);
    };

    const handlePromote = (img: GalleryImage, targetSlot: number) => {
        if (!onPromoteToSlot) return;
        const fullUrl = getImageUrl(img.image);
        onPromoteToSlot(fullUrl, targetSlot, img.id);
        const updated = galleryImages.filter(g => g.id !== img.id);
        setGalleryImages(updated);
        onGalleryLoaded?.(updated);
    };

    const getImageUrl = (imagePath: string) => {
        if (imagePath.startsWith('http')) return imagePath;
        if (typeof window !== 'undefined' && window.location.hostname !== 'localhost') {
            return `https://heroic-healing-production-2365.up.railway.app${imagePath}`;
        }
        return `http://localhost:8000${imagePath}`;
    };

    const hasSlots = availableMainSlots && availableMainSlots.length > 0;

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="border-b border-gray-100 bg-gray-50/50 p-6 flex items-center gap-3">
                <div className="p-2 bg-white rounded-lg shadow-sm">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-teal-500"><rect width="18" height="18" x="3" y="3" rx="2" /><path d="M3 9h18" /><path d="M9 21V9" /></svg>
                </div>
                <h2 className="text-lg font-semibold text-gray-900">Additional Gallery Images</h2>
                {hasSlots && (
                    <span className="ml-auto text-xs text-indigo-600 font-medium bg-indigo-50 px-2.5 py-1 rounded-full border border-indigo-200">
                        ↑ Slots available — promote images above
                    </span>
                )}
            </div>
            <div className="p-6">
                <p className="text-sm text-gray-500 mb-4">Add extra images that will appear in the Vehicle Gallery alongside the 3 main images above</p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    {galleryImages.map((img, index) => (
                        <div key={img.id}>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Image {index + 4}</label>
                            <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200 group">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                    src={getImageUrl(img.image)}
                                    alt={img.caption || `Gallery image ${index + 4}`}
                                    className="w-full h-full object-cover"
                                />
                                <div className="absolute top-1 right-1 flex gap-1">
                                    <span className="bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">Current</span>
                                    <button
                                        type="button"
                                        onClick={() => deleteGalleryImage(img.id)}
                                        className="bg-red-500 text-white text-xs px-2 py-1 rounded shadow-sm hover:bg-red-600 transition-colors"
                                    >
                                        Remove
                                    </button>
                                </div>
                            </div>
                            {hasSlots && onPromoteToSlot && (
                                <div className="flex flex-wrap gap-1.5 mt-1.5">
                                    {availableMainSlots!.map(s => (
                                        <button
                                            key={s.slot}
                                            type="button"
                                            onClick={() => handlePromote(img, s.slot)}
                                            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 hover:border-indigo-300 transition-all"
                                            title={`Move this image to ${s.label}`}
                                        >
                                            <ArrowUp size={12} />
                                            {s.label}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                <div>
                    <label className={`inline-flex items-center gap-2 px-4 py-2 ${uploadingGallery ? 'bg-gray-100 text-gray-400 cursor-wait' : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 cursor-pointer'} rounded-lg border-2 border-dashed border-indigo-300 transition-colors font-semibold`}>
                        <Plus size={20} />
                        {uploadingGallery ? 'Uploading...' : '+ Add More Images'}
                        <input
                            type="file"
                            accept="image/*"
                            multiple
                            disabled={uploadingGallery}
                            onChange={async (e) => {
                                const files = e.target.files;
                                if (!files || files.length === 0 || !articleId) return;
                                e.target.value = '';
                                setUploadingGallery(true);
                                try {
                                    await Promise.all(
                                        Array.from(files).map(file => {
                                            const formData = new FormData();
                                            formData.append('article', articleId);
                                            formData.append('image', file);
                                            formData.append('order', '0');
                                            return api.post('/article-images/', formData, {
                                                headers: { 'Content-Type': 'multipart/form-data' }
                                            });
                                        })
                                    );
                                    await fetchGalleryImages(articleId);
                                } catch (error) {
                                    console.error('Failed to upload gallery images:', error);
                                    alert('Failed to upload some images');
                                } finally {
                                    setUploadingGallery(false);
                                }
                            }}
                            className="hidden"
                        />
                    </label>
                </div>
            </div>
        </div>
    );
}
