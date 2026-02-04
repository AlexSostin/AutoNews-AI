import { MetadataRoute } from 'next';

const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
const SITE_URL = 'https://freshmotors.net';
const FETCH_TIMEOUT = 8000; // 8 seconds timeout

async function fetchWithTimeout(url: string, timeout: number) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            signal: controller.signal,
            next: { revalidate: 3600 },
            headers: {
                'Accept': 'application/json',
            },
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        throw error;
    }
}

async function getArticles() {
    try {
        const res = await fetchWithTimeout(
            `${PRODUCTION_API_URL}/articles/?is_published=true&page_size=100`,
            FETCH_TIMEOUT
        );

        if (!res.ok) {
            console.error(`Failed to fetch articles for sitemap: ${res.status}`);
            return [];
        }
        const data = await res.json();
        return data.results || data || [];
    } catch (e: any) {
        console.error('Error fetching articles for sitemap:', e.message);
        return [];
    }
}

async function getCategories() {
    try {
        const res = await fetchWithTimeout(
            `${PRODUCTION_API_URL}/categories/`,
            FETCH_TIMEOUT
        );

        if (!res.ok) {
            console.error(`Failed to fetch categories for sitemap: ${res.status}`);
            return [];
        }
        const data = await res.json();
        return Array.isArray(data) ? data : (data.results || []);
    } catch (e: any) {
        console.error('Error fetching categories for sitemap:', e.message);
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
