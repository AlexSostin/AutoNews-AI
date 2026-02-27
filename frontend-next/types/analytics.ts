export interface Article {
    id: number;
    title: string;
    slug: string;
    views_count: number;
    views: number;
    created_at: string;
    category?: { name: string };
    name: string;
}

export interface Stats {
    total_articles: number;
    total_views: number;
    total_comments: number;
    total_subscribers: number;
    articles_growth: number;
    views_growth: number;
    comments_growth: number;
    subscribers_growth: number;
}

export interface TimelineData {
    labels: string[];
    data: number[];
}

export interface CategoriesData {
    labels: string[];
    data: number[];
}

export interface GSCStats {
    timeline: {
        labels: string[];
        clicks: number[];
        impressions: number[];
    };
    summary: {
        clicks: number;
        impressions: number;
        ctr: number;
        position: number;
    };
    previous_summary: {
        clicks: number;
        impressions: number;
        ctr: number;
        position: number;
    };
    last_sync: string | null;
}

export interface AIStats {
    enrichment: {
        total_articles: number;
        vehicle_specs: number;
        ab_titles: number;
        tags: number;
        car_specs: number;
        images: number;
    };
    top_tags: {
        name: string;
        slug: string;
        article_count: number;
        total_views: number;
    }[];
    sources: {
        youtube: number;
        rss: number;
        translated: number;
    };
}

export interface AIGenerationStats {
    spec_coverage: {
        total_with_specs: number;
        total_articles: number;
        overall_pct: number;
        per_field: Record<string, number>;
    };
    generation_time: {
        avg_seconds?: number;
        median_seconds?: number;
        max_seconds?: number;
        sample_size?: number;
    };
    edit_rates: {
        avg_edit_pct?: number;
        median_edit_pct?: number;
        max_edit_pct?: number;
        unedited_count?: number;
        sample_size?: number;
    };
}

export interface PopularModel {
    make: string;
    model: string;
    label: string;
    total_views: number;
    article_count: number;
}

export interface ProviderStatsData {
    providers: Record<string, {
        avg_quality: number;
        avg_coverage: number;
        avg_time: number;
        count: number;
    }>;
    total_records: number;
}

export interface ABVariant {
    id: number;
    variant: string;
    title: string;
    impressions: number;
    clicks: number;
    ctr: number;
    is_winner: boolean;
    is_active: boolean;
}

export interface ABTest {
    article_id: number;
    article_title: string;
    article_slug: string;
    is_active: boolean;
    total_impressions: number;
    winner: string | null;
    variants: ABVariant[];
}
