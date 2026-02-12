'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Save, Plus, X } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';

interface Category {
  id: number;
  name: string;
  slug: string;
}

interface Tag {
  id: number;
  name: string;
  slug: string;
  group_name?: string;
}

interface ArticleData {
  id: number;
  title: string;
  slug: string;
  summary: string;
  content: string;
  categories: { id: number; name: string; slug: string }[];
  tags: number[];
  published: boolean;
  is_hero: boolean;
  youtube_url: string;
}

interface GalleryImage {
  id: number;
  image: string;
  caption: string;
  order: number;
}

export default function EditArticlePage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const [articleId, setArticleId] = useState<string | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [galleryImages, setGalleryImages] = useState<GalleryImage[]>([]);
  const [newGalleryImages, setNewGalleryImages] = useState<File[]>([]);
  const [uploadingGallery, setUploadingGallery] = useState(false);

  const [formData, setFormData] = useState({
    title: '',
    slug: '',
    summary: '',
    content: '',
    category_ids: [] as number[],
    tags: [] as number[],
    published: false,
    is_hero: false,
    youtube_url: '',
    author_name: '',
    author_channel_url: '',
    image: null as File | null,
    image_2: null as File | null,
    image_3: null as File | null,
    current_image: '',
    current_image_2: '',
    current_image_3: '',
    delete_image: false,
    delete_image_2: false,
    delete_image_3: false,
  });

  useEffect(() => {
    params.then(({ id }) => {
      setArticleId(id);
      fetchData(id);
    });
  }, [params]);

  const fetchData = async (id: string) => {
    try {
      const [articleRes, categoriesRes, tagsRes] = await Promise.all([
        api.get(`/articles/${id}/`),
        api.get('/categories/'),
        api.get('/tags/')
      ]);

      const article = articleRes.data;

      // Helper to build full image URL (runtime detection)
      const getMediaUrl = () => {
        if (typeof window !== 'undefined') {
          const host = window.location.hostname;
          if (host !== 'localhost' && host !== '127.0.0.1') {
            return 'https://heroic-healing-production-2365.up.railway.app';
          }
        }
        return 'http://localhost:8000';
      };

      const buildImageUrl = (path: string) => {
        if (!path) return '';
        if (path.startsWith('http://') || path.startsWith('https://')) return path;
        return `${getMediaUrl()}${path}`;
      };

      setFormData({
        title: article.title || '',
        slug: article.slug || '',
        summary: article.summary || '',
        content: article.content || '',
        category_ids: Array.isArray(article.categories) ? article.categories.map((cat: any) => cat.id) : [],
        tags: Array.isArray(article.tags) ? article.tags.map((tag: any) => tag.id) : [],
        published: article.is_published ?? false,
        is_hero: article.is_hero ?? false,
        youtube_url: article.youtube_url || '',
        author_name: article.author_name || '',
        author_channel_url: article.author_channel_url || '',
        image: null,
        image_2: null,
        image_3: null,
        current_image: buildImageUrl(article.thumbnail_url || article.image || ''),
        current_image_2: buildImageUrl(article.image_2_url || article.image_2 || ''),
        current_image_3: buildImageUrl(article.image_3_url || article.image_3 || ''),
        delete_image: false,
        delete_image_2: false,
        delete_image_3: false,
      });

      // Handle both array and paginated response
      setCategories(Array.isArray(categoriesRes.data) ? categoriesRes.data : categoriesRes.data.results || []);
      setTags(Array.isArray(tagsRes.data) ? tagsRes.data : tagsRes.data.results || []);

      // Fetch gallery images
      await fetchGalleryImages(id);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      alert('Failed to load article');
    } finally {
      setLoading(false);
    }
  };

  const fetchGalleryImages = async (articleId: string) => {
    try {
      const response = await api.get(`/article-images/?article=${articleId}`);
      setGalleryImages(response.data.results || response.data || []);
    } catch (error) {
      console.error('Failed to fetch gallery images:', error);
    }
  };

  const handleGalleryImageUpload = async (files: FileList | null) => {
    if (!files || !articleId) return;

    const filesArray = Array.from(files);
    setNewGalleryImages(prev => [...prev, ...filesArray]);
  };

  const removeNewGalleryImage = (index: number) => {
    setNewGalleryImages(prev => prev.filter((_, i) => i !== index));
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
      for (const file of newGalleryImages) {
        const formData = new FormData();
        formData.append('article', articleId);
        formData.append('image', file);
        formData.append('order', '0');

        await api.post('/article-images/', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      }

      // Refresh gallery images
      await fetchGalleryImages(articleId);
      setNewGalleryImages([]);
    } catch (error) {
      console.error('Failed to upload gallery images:', error);
      alert('Failed to upload some images');
    } finally {
      setUploadingGallery(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!articleId) return;

    setSaving(true);
    try {
      // Use FormData if images are being uploaded
      if (formData.image || formData.image_2 || formData.image_3) {
        const formDataToSend = new FormData();
        formDataToSend.append('title', formData.title);
        formDataToSend.append('summary', formData.summary);
        formDataToSend.append('content', formData.content);
        formData.category_ids.forEach(id => formDataToSend.append('category_ids', id.toString()));
        formDataToSend.append('tag_ids', JSON.stringify(formData.tags));
        formDataToSend.append('is_published', formData.published.toString());
        formDataToSend.append('is_hero', formData.is_hero.toString());

        if (formData.youtube_url) {
          formDataToSend.append('youtube_url', formData.youtube_url);
        }
        if (formData.author_name) {
          formDataToSend.append('author_name', formData.author_name);
        }
        if (formData.author_channel_url) {
          formDataToSend.append('author_channel_url', formData.author_channel_url);
        }

        if (formData.image) {
          formDataToSend.append('image', formData.image);
        }
        if (formData.image_2) {
          formDataToSend.append('image_2', formData.image_2);
        }
        if (formData.image_3) {
          formDataToSend.append('image_3', formData.image_3);
        }

        // Handle image deletion
        if (formData.delete_image) formDataToSend.append('delete_image', 'true');
        if (formData.delete_image_2) formDataToSend.append('delete_image_2', 'true');
        if (formData.delete_image_3) formDataToSend.append('delete_image_3', 'true');

        await api.put(`/articles/${articleId}/`, formDataToSend, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      } else {
        // No images - use JSON
        const payload = {
          title: formData.title,
          summary: formData.summary,
          content: formData.content,
          category_ids: formData.category_ids,
          tag_ids: formData.tags,
          is_published: formData.published,
          is_hero: formData.is_hero,
          youtube_url: formData.youtube_url,
          author_name: formData.author_name,
          author_channel_url: formData.author_channel_url,
        };

        await api.put(`/articles/${articleId}/`, payload);
      }

      // Upload gallery images if any
      await uploadGalleryImages();

      alert('Article updated successfully!');
      router.push('/admin/articles');
    } catch (error: any) {
      console.error('Failed to update article:', error);
      alert('Failed to update article: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  const handleTagToggle = (tagId: number) => {
    setFormData({
      ...formData,
      tags: formData.tags.includes(tagId)
        ? formData.tags.filter(id => id !== tagId)
        : [...formData.tags, tagId],
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="text-gray-600 mt-4 font-medium">Loading article...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <Link
          href="/admin/articles"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft size={24} />
        </Link>
        <h1 className="text-3xl font-black text-gray-950">Edit Article</h1>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-6">
        <div className="space-y-6">
          {/* Title */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Title *</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              required
            />
          </div>

          {/* Slug */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">
              Slug <span className="text-sm font-normal text-gray-600">(auto-generated from title)</span>
            </label>
            <input
              type="text"
              value={formData.slug}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg bg-gray-50 text-gray-700 font-medium cursor-not-allowed"
              disabled
            />
          </div>

          {/* YouTube URL */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">YouTube URL</label>
            <input
              type="url"
              value={formData.youtube_url}
              onChange={(e) => setFormData({ ...formData, youtube_url: e.target.value })}
              placeholder="https://youtube.com/watch?v=..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
            />
          </div>

          {/* Content Source Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Content Source</label>
              <input
                type="text"
                value={formData.author_name}
                onChange={(e) => setFormData({ ...formData, author_name: e.target.value })}
                placeholder="e.g., Toyota Global, Doug DeMuro, Carwow"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Source URL</label>
              <input
                type="url"
                value={formData.author_channel_url}
                onChange={(e) => setFormData({ ...formData, author_channel_url: e.target.value })}
                placeholder="https://global.toyota/... or YouTube channel"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              />
            </div>
          </div>

          {/* Summary */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Summary *</label>
            <textarea
              value={formData.summary}
              onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
              rows={3}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              required
            />
          </div>

          {/* Content */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Content (HTML) *</label>
            <textarea
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              rows={12}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-mono text-sm"
              required
            />
          </div>

          {/* Images Section */}
          <div className="border-t pt-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Images</h3>
            <p className="text-sm text-gray-600 mb-4">Replace images or keep existing ones from AI generation</p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Image 1 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 1 (Main)</label>
                {formData.current_image && !formData.delete_image && (
                  <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200 group">
                    <img
                      src={formData.current_image}
                      alt="Current Image 1"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-1 right-1 flex gap-1">
                      <span className="bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">Current</span>
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, delete_image: true })}
                        className="bg-red-500 text-white text-xs px-2 py-1 rounded shadow-sm hover:bg-red-600 transition-colors"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                )}
                {formData.delete_image && (
                  <div className="mb-2 text-sm text-red-600 bg-red-50 p-2 rounded border border-red-200 flex justify-between items-center">
                    <span>Marked for deletion</span>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, delete_image: false })}
                      className="text-gray-600 underline text-xs hover:text-gray-900"
                    >
                      Undo
                    </button>
                  </div>
                )}
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFormData({ ...formData, image: e.target.files?.[0] || null, delete_image: false })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm text-gray-900 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 transition-all"
                />
                {formData.image && (
                  <p className="text-xs text-green-600 mt-1">✓ Will replace with: {formData.image.name}</p>
                )}
              </div>

              {/* Image 2 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 2</label>
                {formData.current_image_2 && !formData.delete_image_2 && (
                  <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200">
                    <img
                      src={formData.current_image_2}
                      alt="Current Image 2"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-1 right-1 flex gap-1">
                      <span className="bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">Current</span>
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, delete_image_2: true })}
                        className="bg-red-500 text-white text-xs px-2 py-1 rounded shadow-sm hover:bg-red-600 transition-colors"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                )}
                {formData.delete_image_2 && (
                  <div className="mb-2 text-sm text-red-600 bg-red-50 p-2 rounded border border-red-200 flex justify-between items-center">
                    <span>Marked for deletion</span>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, delete_image_2: false })}
                      className="text-gray-600 underline text-xs hover:text-gray-900"
                    >
                      Undo
                    </button>
                  </div>
                )}
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFormData({ ...formData, image_2: e.target.files?.[0] || null, delete_image_2: false })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm text-gray-900 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 transition-all"
                />
                {formData.image_2 && (
                  <p className="text-xs text-green-600 mt-1">✓ Will replace with: {formData.image_2.name}</p>
                )}
              </div>

              {/* Image 3 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 3</label>
                {formData.current_image_3 && !formData.delete_image_3 && (
                  <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200">
                    <img
                      src={formData.current_image_3}
                      alt="Current Image 3"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-1 right-1 flex gap-1">
                      <span className="bg-green-500 text-white text-xs px-2 py-1 rounded shadow-sm">Current</span>
                      <button
                        type="button"
                        onClick={() => setFormData({ ...formData, delete_image_3: true })}
                        className="bg-red-500 text-white text-xs px-2 py-1 rounded shadow-sm hover:bg-red-600 transition-colors"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                )}
                {formData.delete_image_3 && (
                  <div className="mb-2 text-sm text-red-600 bg-red-50 p-2 rounded border border-red-200 flex justify-between items-center">
                    <span>Marked for deletion</span>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, delete_image_3: false })}
                      className="text-gray-600 underline text-xs hover:text-gray-900"
                    >
                      Undo
                    </button>
                  </div>
                )}
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFormData({ ...formData, image_3: e.target.files?.[0] || null, delete_image_3: false })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm text-gray-900 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 transition-all"
                />
                {formData.image_3 && (
                  <p className="text-xs text-green-600 mt-1">✓ Will replace with: {formData.image_3.name}</p>
                )}
              </div>
            </div>
          </div>

          {/* Gallery Images Section */}
          <div className="border-t pt-6">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Additional Gallery Images</h3>
            <p className="text-sm text-gray-600 mb-4">Add extra images that will appear in the Vehicle Gallery alongside the 3 main images above</p>

            {/* Existing Gallery Images as individual cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              {galleryImages.map((img, index) => (
                <div key={img.id}>
                  <label className="block text-sm font-bold text-gray-900 mb-2">Image {index + 4}</label>
                  <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200 group">
                    <img
                      src={img.image.startsWith('http') ? img.image : `${typeof window !== 'undefined' && window.location.hostname !== 'localhost' ? 'https://heroic-healing-production-2365.up.railway.app' : 'http://localhost:8000'}${img.image}`}
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

              {/* New gallery images to upload - individual cards */}
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

            {/* Add Image Button */}
            <div>
              <label className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-700 rounded-lg border-2 border-dashed border-indigo-300 hover:bg-indigo-100 transition-colors cursor-pointer font-semibold">
                <Plus size={20} />
                + Add More Images
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => {
                    if (e.target.files?.[0]) {
                      setNewGalleryImages(prev => [...prev, e.target.files![0]]);
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

          {/* Categories */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Categories *</label>
            <div className="flex flex-wrap gap-2">
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => {
                    const ids = formData.category_ids.includes(cat.id)
                      ? formData.category_ids.filter(id => id !== cat.id)
                      : [...formData.category_ids, cat.id];
                    setFormData({ ...formData, category_ids: ids });
                  }}
                  className={`px-4 py-2 rounded-lg text-sm font-bold transition-all border-2 ${formData.category_ids.includes(cat.id)
                    ? 'bg-indigo-600 border-indigo-600 text-white shadow-md'
                    : 'bg-white border-gray-200 text-gray-700 hover:border-indigo-300'
                    }`}
                >
                  {cat.name}
                  {formData.category_ids.includes(cat.id) && (
                    <span className="ml-2">✓</span>
                  )}
                </button>
              ))}
            </div>
            {formData.category_ids.length === 0 && (
              <p className="text-sm text-red-500 mt-1">Select at least one category</p>
            )}
          </div>

          {/* Tags */}
          <div className="border-t pt-6">
            <label className="block text-lg font-bold text-gray-900 mb-4">Tags & Categories</label>
            <p className="text-sm text-gray-600 mb-6">Select relevant tags grouped by category</p>

            <div className="space-y-8">
              {Object.entries(
                tags.reduce((acc, tag) => {
                  const group = tag.group_name || 'General';
                  if (!acc[group]) acc[group] = [];
                  acc[group].push(tag);
                  return acc;
                }, {} as Record<string, Tag[]>)
              ).sort(([a], [b]) => {
                // Keep 'General' at the bottom
                if (a === 'General') return 1;
                if (b === 'General') return -1;
                return a.localeCompare(b);
              }).map(([groupName, groupTags]) => (
                <div key={groupName} className="bg-gray-50/50 rounded-xl p-4 sm:p-5 border border-gray-100">
                  <h4 className="text-sm font-black text-indigo-900 uppercase tracking-wider mb-4 flex items-center gap-2">
                    <span className="w-2 h-2 bg-indigo-600 rounded-full"></span>
                    {groupName}
                  </h4>
                  <div className="flex flex-wrap gap-2 sm:gap-3">
                    {groupTags.map((tag) => (
                      <button
                        key={tag.id}
                        type="button"
                        onClick={() => handleTagToggle(tag.id)}
                        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all border-2 ${formData.tags.includes(tag.id)
                          ? 'bg-indigo-600 border-indigo-600 text-white shadow-md scale-105'
                          : 'bg-white border-gray-200 text-gray-700 hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50/50'
                          }`}
                      >
                        {tag.name}
                        {formData.tags.includes(tag.id) && (
                          <span className="ml-2 inline-flex items-center justify-center w-4 h-4 bg-white/20 rounded-full text-[10px]">✓</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap gap-8">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="published"
                checked={formData.published}
                onChange={(e) => setFormData({ ...formData, published: e.target.checked })}
                className="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="published" className="text-sm font-bold text-gray-900 cursor-pointer">
                Published (Visible on site)
              </label>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="is_hero"
                checked={formData.is_hero}
                onChange={(e) => setFormData({ ...formData, is_hero: e.target.checked })}
                className="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
              />
              <label htmlFor="is_hero" className="text-sm font-bold text-gray-900 cursor-pointer">
                Hero (Promote to homepage banner)
              </label>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex gap-4 pt-4">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md flex items-center justify-center gap-2"
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Saving...
                </>
              ) : (
                <>
                  <Save size={20} />
                  Save Changes
                </>
              )}
            </button>
            <Link
              href="/admin/articles"
              className="px-6 py-3 bg-gray-200 text-gray-800 rounded-lg font-bold hover:bg-gray-300 transition-colors"
            >
              Cancel
            </Link>
          </div>
        </div>
      </form>
    </div>
  );
}
