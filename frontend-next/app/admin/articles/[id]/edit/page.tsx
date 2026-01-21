'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Save } from 'lucide-react';
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
}

interface ArticleData {
  id: number;
  title: string;
  slug: string;
  summary: string;
  content: string;
  category: number;
  tags: number[];
  published: boolean;
  youtube_url: string;
}

export default function EditArticlePage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const [articleId, setArticleId] = useState<string | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  const [formData, setFormData] = useState({
    title: '',
    slug: '',
    summary: '',
    content: '',
    category: '',
    tags: [] as number[],
    published: false,
    youtube_url: '',
    image: null as File | null,
    image_2: null as File | null,
    image_3: null as File | null,
    current_image: '',
    current_image_2: '',
    current_image_3: '',
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
        return 'http://localhost:8001';
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
        category: article.category?.id?.toString() || '',
        tags: Array.isArray(article.tags) ? article.tags.map((tag: any) => tag.id) : [],
        published: article.is_published ?? false,
        youtube_url: article.youtube_url || '',
        image: null,
        image_2: null,
        image_3: null,
        current_image: buildImageUrl(article.thumbnail_url || article.image || ''),
        current_image_2: buildImageUrl(article.image_2_url || article.image_2 || ''),
        current_image_3: buildImageUrl(article.image_3_url || article.image_3 || ''),
      });

      // Handle both array and paginated response
      setCategories(Array.isArray(categoriesRes.data) ? categoriesRes.data : categoriesRes.data.results || []);
      setTags(Array.isArray(tagsRes.data) ? tagsRes.data : tagsRes.data.results || []);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      alert('Failed to load article');
    } finally {
      setLoading(false);
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
        formDataToSend.append('category_id', formData.category);
        formDataToSend.append('tag_ids', JSON.stringify(formData.tags));
        formDataToSend.append('is_published', formData.published.toString());
        
        if (formData.youtube_url) {
          formDataToSend.append('youtube_url', formData.youtube_url);
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
          category_id: parseInt(formData.category),
          tag_ids: formData.tags,
          is_published: formData.published,
          youtube_url: formData.youtube_url,
        };

        await api.put(`/articles/${articleId}/`, payload);
      }
      
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
                {formData.current_image && (
                  <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200">
                    <img 
                      src={formData.current_image} 
                      alt="Current Image 1" 
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-1 right-1 bg-green-500 text-white text-xs px-2 py-1 rounded">Current</div>
                  </div>
                )}
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFormData({ ...formData, image: e.target.files?.[0] || null })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm"
                />
                {formData.image && (
                  <p className="text-xs text-green-600 mt-1">✓ Will replace with: {formData.image.name}</p>
                )}
              </div>

              {/* Image 2 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 2</label>
                {formData.current_image_2 && (
                  <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200">
                    <img 
                      src={formData.current_image_2} 
                      alt="Current Image 2" 
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-1 right-1 bg-green-500 text-white text-xs px-2 py-1 rounded">Current</div>
                  </div>
                )}
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFormData({ ...formData, image_2: e.target.files?.[0] || null })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm"
                />
                {formData.image_2 && (
                  <p className="text-xs text-green-600 mt-1">✓ Will replace with: {formData.image_2.name}</p>
                )}
              </div>

              {/* Image 3 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 3</label>
                {formData.current_image_3 && (
                  <div className="mb-2 relative h-32 rounded-lg overflow-hidden border-2 border-gray-200">
                    <img 
                      src={formData.current_image_3} 
                      alt="Current Image 3" 
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-1 right-1 bg-green-500 text-white text-xs px-2 py-1 rounded">Current</div>
                  </div>
                )}
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFormData({ ...formData, image_3: e.target.files?.[0] || null })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm"
                />
                {formData.image_3 && (
                  <p className="text-xs text-green-600 mt-1">✓ Will replace with: {formData.image_3.name}</p>
                )}
              </div>
            </div>
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Category *</label>
            <select
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              required
            >
              <option value="">Select a category</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>

          {/* Tags */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-3">Tags</label>
            <div className="flex flex-wrap gap-2">
              {tags.map((tag) => (
                <button
                  key={tag.id}
                  type="button"
                  onClick={() => handleTagToggle(tag.id)}
                  className={`px-4 py-2 rounded-full font-medium transition-all ${
                    formData.tags.includes(tag.id)
                      ? 'bg-indigo-600 text-white shadow-md'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {tag.name}
                </button>
              ))}
            </div>
          </div>

          {/* Published Status */}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="published"
              checked={formData.published}
              onChange={(e) => setFormData({ ...formData, published: e.target.checked })}
              className="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
            />
            <label htmlFor="published" className="text-sm font-bold text-gray-900">
              Published
            </label>
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
