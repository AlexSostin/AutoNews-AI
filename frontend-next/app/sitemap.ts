import { MetadataRoute } from 'next';

const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const SITE_URL = 'https://freshmotors.net';

async function getArticles() {
    try {
        const res = await fetch(`${PRODUCTION_API_URL}/articles/?is_published=true&page_size=100`, {
            next: { revalidate: 3600 },
            headers: {
                'Accept': 'application/json',
            },
        });
        if (!res.ok) {
            console.error(`Failed to fetch articles for sitemap: ${res.status}`);
            return [];
        }
        const data = await res.json();
        return data.results || data || [];
    } catch (e) {
        console.error('Error fetching articles for sitemap:', e);
        return [];
    }
}

async function getCategories() {
    try {
        const res = await fetch(`${PRODUCTION_API_URL}/categories/`, {
            next: { revalidate: 3600 },
            headers: {
                'Accept': 'application/json',
            },
        });
        if (!res.ok) {
            console.error(`Failed to fetch categories for sitemap: ${res.status}`);
            return [];
        }
        const data = await res.json();
        return Array.isArray(data) ? data : (data.results || []);
    } catch (e) {
        console.error('Error fetching categories for sitemap:', e);
        return [];
    }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
    const articles = await getArticles();
    const categories = await getCategories();

    const articleEntries = articles.map((article: any) => ({
        url: `${SITE_URL}/articles/${article.slug}`,
        lastModified: new Date(article.updated_at || article.created_at),
        changeFrequency: 'weekly' as const,
        priority: 0.7,
    }));

    const categoryEntries = categories.map((category: any) => ({
        url: `${SITE_URL}/categories/${category.slug}`,
        lastModified: new Date(),
        changeFrequency: 'weekly' as const,
        priority: 0.6,
    }));

    return [
        {
            url: SITE_URL,
            lastModified: new Date(),
            changeFrequency: 'daily' as const,
            priority: 1,
        },
        {
            url: `${SITE_URL}/articles`,
            lastModified: new Date(),
            changeFrequency: 'daily' as const,
            priority: 0.8,
        },
        ...articleEntries,
        ...categoryEntries,
    ];
}
