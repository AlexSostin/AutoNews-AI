// Google Analytics 4 event tracking utilities

declare global {
    interface Window {
        gtag?: (...args: any[]) => void;
    }
}

export const trackEvent = (eventName: string, params?: Record<string, any>) => {
    if (typeof window !== 'undefined' && window.gtag) {
        window.gtag('event', eventName, params);
    }
};

// Article events
export const trackArticleView = (articleId: number, title: string, category?: string) => {
    trackEvent('article_view', {
        article_id: articleId,
        article_title: title,
        category: category,
        engagement_time_msec: 100,
    });
};

export const trackArticleRead = (articleId: number, readPercentage: number) => {
    trackEvent('article_read', {
        article_id: articleId,
        read_percentage: readPercentage,
        value: readPercentage,
    });
};

export const trackShare = (platform: string, articleId: number, articleTitle: string) => {
    trackEvent('share', {
        method: platform,
        content_type: 'article',
        item_id: articleId,
        content_name: articleTitle,
    });
};

export const trackSearch = (searchTerm: string, resultsCount?: number) => {
    trackEvent('search', {
        search_term: searchTerm,
        ...(resultsCount !== undefined && { results_count: resultsCount }),
    });
};

export const trackNewsletterSignup = (method: string = 'footer_form') => {
    trackEvent('newsletter_signup', {
        method: method,
    });
};

export const trackVideoPlay = (videoUrl: string, articleId?: number) => {
    trackEvent('video_start', {
        video_url: videoUrl,
        ...(articleId && { article_id: articleId }),
    });
};

export const trackCommentPost = (articleId: number) => {
    trackEvent('comment_post', {
        article_id: articleId,
    });
};

export const trackFavorite = (articleId: number, action: 'add' | 'remove') => {
    trackEvent('favorite', {
        article_id: articleId,
        action: action,
    });
};

export const trackRating = (articleId: number, rating: number) => {
    trackEvent('article_rating', {
        article_id: articleId,
        rating: rating,
    });
};

// Page view tracking (for SPA navigation)
export const trackPageView = (url: string, title: string) => {
    if (typeof window !== 'undefined' && window.gtag) {
        window.gtag('config', process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID || '', {
            page_path: url,
            page_title: title,
        });
    }
};
