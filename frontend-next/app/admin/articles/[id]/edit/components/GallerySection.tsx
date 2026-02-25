import { Plus } from 'lucide-react';
import React, { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
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

interface GallerySectionProps {
    articleId: string | null;
}

export const GallerySection = forwardRef<GallerySectionRef, GallerySectionProps>(({ articleId }, ref) => {
    const [galleryImages, setGalleryImages] = useState<GalleryImage[]>([]);
    const [newGalleryImages, setNewGalleryImages] = useState<File[]>([]);
    const [uploadingGallery, setUploadingGallery] = useState(false);

    useEffect(() => {
        if (articleId) {
            fetchGalleryImages(articleId);
        }
    }, [articleId]);

    const fetchGalleryImages = async (id: string) => {
        try {
            const response = await api.get(`/article-images/?article=${id}`);
            setGalleryImages(response.data.results || response.data || []);
        } catch (error) {
            console.error('Failed to fetch gallery images:', error);
        }
    };

    const deleteGalleryImage = async (imageId: number) => {
        if (!confirm('Delete this gallery image?')) return;
        try {
            await api.delete(`/article-images/${imageId}/`);
            setGalleryImages(prev => prev.filter(img => img.id !== imageId));
        } catch (error) {
            console.error('Failed to delete gallery image:', error);
            alert('Failed to delete image');
        }
    };

    const uploadGalleryImages = async () => {
        if (newGalleryImages.length === 0 || !articleId) return;
        setUploadingGallery(true);
        try {
            await Promise.all(
                newGalleryImages.map(file => {
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
            setNewGalleryImages([]);
        } catch (error) {
            console.error('Failed to upload gallery images:', error);
            alert('Failed to upload some images');
        } finally {
            setUploadingGallery(false);
        }
    };

    useImperativeHandle(ref, () => ({
        upload: uploadGalleryImages
    }));

    const removeNewGalleryImage = (index: number) => {
        setNewGalleryImages(prev => prev.filter((_, i) => i !== index));
    };

    const getImageUrl = (imagePath: string) => {
        if (imagePath.startsWith('http')) return imagePath;
        if (typeof window !== 'undefined' && window.location.hostname !== 'localhost') {
            return `https://heroic-healing-production-2365.up.railway.app${imagePath}`;
        }
        return `http://localhost:8000${imagePath}`;
    };

    return (
        <div className="border-t pt-6">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Additional Gallery Images</h3>
            <p className="text-sm text-gray-600 mb-4">Add extra images that will appear in the Vehicle Gallery alongside the 3 main images above</p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                {galleryImages.map((img, index) => (
                    <div key={img.id}>
                        <label className="block text-sm font-bold text-gray-900 mb-2">Image {index + 4}</label>
                        <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200 group">
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
                    </div>
                ))}

                {newGalleryImages.map((file, index) => (
                    <div key={`new-${index}`}>
                        <label className="block text-sm font-bold text-gray-900 mb-2">Image {galleryImages.length + index + 4}</label>
                        <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-green-300 group">
                            <img
                                src={URL.createObjectURL(file)}
                                alt={file.name}
                                className="w-full h-full object-cover"
                            />
                            <div className="absolute top-1 right-1 flex gap-1">
                                <span className="bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">New</span>
                                <button
                                    type="button"
                                    onClick={() => removeNewGalleryImage(index)}
                                    className="bg-red-500 text-white text-xs px-2 py-1 rounded shadow-sm hover:bg-red-600 transition-colors"
                                >
                                    Remove
                                </button>
                            </div>
                        </div>
                        <p className="text-xs text-green-600 mt-1">✓ Will upload: {file.name}</p>
                    </div>
                ))}
            </div>

            <div>
                <label className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-700 rounded-lg border-2 border-dashed border-indigo-300 hover:bg-indigo-100 transition-colors cursor-pointer font-semibold">
                    <Plus size={20} />
                    + Add More Images
                    <input
                        type="file"
                        accept="image/*"
                        onChange={(e) => {
                            if (e.target.files?.[0]) {
                                const newFile = e.target.files[0];
                                setNewGalleryImages(prev => [...prev, newFile]);
                                e.target.value = '';
                            }
                        }}
                        className="hidden"
                    />
                </label>
                {uploadingGallery && (
                    <span className="ml-3 text-sm text-gray-600">Uploading...</span>
                )}
            </div>
        </div>
    );
});

