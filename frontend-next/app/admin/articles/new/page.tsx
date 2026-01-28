'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Youtube, Sparkles, Save } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';
import GenerationProgress from '@/components/admin/GenerationProgress';

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

export default function NewArticlePage() {
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [taskId, setTaskId] = useState<string>('');

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
  });

  useEffect(() => {
    fetchCategoriesAndTags();
  }, []);

  const fetchCategoriesAndTags = async () => {
    try {
      const [categoriesRes, tagsRes] = await Promise.all([
        api.get('/categories/'),
        api.get('/tags/')
      ]);
      // Handle both array and paginated response
      setCategories(Array.isArray(categoriesRes.data) ? categoriesRes.data : categoriesRes.data.results || []);
      setTags(Array.isArray(tagsRes.data) ? tagsRes.data : tagsRes.data.results || []);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  };

  const generateSlug = (title: string) => {
    return title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
  };

  const handleTitleChange = (title: string) => {
    setFormData({
      ...formData,
      title,
      slug: generateSlug(title),
    });
  };

  const handleGenerateFromYoutube = async () => {
    if (!formData.youtube_url) {
      alert('Please enter a YouTube URL');
      return;
    }

    // Generate unique task ID for WebSocket tracking
    const newTaskId = `gen_${Date.now()}_${Math.random().toString(36).substring(7)}`;
    setTaskId(newTaskId);
    setGenerating(true);

    try {
      const response = await api.post('/articles/generate_from_youtube/', {
        youtube_url: formData.youtube_url,
        task_id: newTaskId,
        provider: 'groq'
      });

      if (response.data.success) {
        // Progress component will handle completion, just redirect
        router.push(`/admin/articles/${response.data.article.id}/edit`);
      } else {
        alert('Failed to generate article: ' + response.data.error);
        setGenerating(false);
        setTaskId('');
      }
    } catch (error: any) {
      console.error('Generation error:', error);
      alert('Failed to generate article: ' + (error.response?.data?.error || error.message));
      setGenerating(false);
      setTaskId('');
    }
  };

  const handleGenerationComplete = (success: boolean, articleId?: number) => {
    setGenerating(false);
    setTaskId('');
    if (success && articleId) {
      router.push(`/admin/articles/${articleId}/edit`);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Use FormData to handle file uploads
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

      // Add images if selected
      if (formData.image) {
        formDataToSend.append('image', formData.image);
      }
      if (formData.image_2) {
        formDataToSend.append('image_2', formData.image_2);
      }
      if (formData.image_3) {
        formDataToSend.append('image_3', formData.image_3);
      }

      const response = await api.post('/articles/', formDataToSend, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      alert('Article created successfully!');
      router.push('/admin/articles');
    } catch (error: any) {
      console.error('Failed to create article:', error);
      alert('Failed to create article: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
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

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <Link
          href="/admin/articles"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft size={24} />
        </Link>
        <h1 className="text-3xl font-black text-gray-950">Create New Article</h1>
      </div>

      {/* AI Generation Section */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border-2 border-indigo-200 rounded-xl p-6 mb-6">
        <div className="flex items-start gap-4">
          <div className="bg-indigo-600 p-3 rounded-lg">
            <Sparkles className="text-white" size={24} />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-black text-gray-950 mb-2">AI-Powered Article Generation</h3>
            <p className="text-gray-700 font-medium mb-4">
              Generate a complete automotive article from a YouTube video using Groq AI (10x faster than ChatGPT!)
            </p>
            <div className="flex flex-wrap sm:flex-nowrap gap-3">
              <div className="flex-1 min-w-[200px] relative">
                <Youtube className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="url"
                  placeholder="https://youtube.com/watch?v=..."
                  value={formData.youtube_url}
                  onChange={(e) => setFormData({ ...formData, youtube_url: e.target.value })}
                  className="w-full pl-10 pr-4 py-3 border-2 border-indigo-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
                  disabled={generating}
                />
              </div>

              <button
                type="button"
                onClick={handleGenerateFromYoutube}
                disabled={generating || !formData.youtube_url}
                className="px-4 sm:px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md flex items-center gap-2 whitespace-nowrap w-full sm:w-auto justify-center"
              >
                {generating ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles size={20} />
                    Generate with AI
                  </>
                )}
              </button>
            </div>

            {/* Progress Component */}
            {generating && taskId && (
              <div className="mt-4">
                <GenerationProgress
                  taskId={taskId}
                  isGenerating={generating}
                  onComplete={handleGenerationComplete}
                />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Manual Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-6">
        <div className="space-y-6">
          {/* Title */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Title *</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => handleTitleChange(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              required
            />
          </div>

          {/* Slug */}
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Slug *</label>
            <input
              type="text"
              value={formData.slug}
              onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 font-medium"
              required
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
            <h3 className="text-lg font-bold text-gray-900 mb-4">Images (Optional)</h3>
            <p className="text-sm text-gray-600 mb-4">Upload up to 3 images or they will be auto-extracted from YouTube during AI generation</p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Image 1 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 1 (Main)</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFormData({ ...formData, image: e.target.files?.[0] || null })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm text-gray-900 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 transition-all"
                />
                {formData.image && (
                  <p className="text-xs text-green-600 mt-1">✓ {formData.image.name}</p>
                )}
              </div>

              {/* Image 2 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 2</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFormData({ ...formData, image_2: e.target.files?.[0] || null })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm text-gray-900 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 transition-all"
                />
                {formData.image_2 && (
                  <p className="text-xs text-green-600 mt-1">✓ {formData.image_2.name}</p>
                )}
              </div>

              {/* Image 3 */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Image 3</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setFormData({ ...formData, image_3: e.target.files?.[0] || null })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm text-gray-900 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 transition-all"
                />
                {formData.image_3 && (
                  <p className="text-xs text-green-600 mt-1">✓ {formData.image_3.name}</p>
                )}
              </div>
            </div>
          </div>

          {/* onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
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
                  className={`px-4 py-2 rounded-full font-medium transition-all ${formData.tags.includes(tag.id)
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
              Publish immediately
            </label>
          </div>

          {/* Submit Button */}
          <div className="flex gap-4 pt-4">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Creating...
                </>
              ) : (
                <>
                  <Save size={20} />
                  Create Article
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
