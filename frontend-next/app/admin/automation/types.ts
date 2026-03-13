export interface AutomationSettings {
    site_theme: string;
    rss_scan_enabled: boolean;
    rss_scan_interval_minutes: number;
    rss_max_articles_per_scan: number;
    rss_last_run: string | null;
    rss_last_status: string;
    rss_articles_today: number;
    youtube_scan_enabled: boolean;
    youtube_scan_interval_minutes: number;
    youtube_max_videos_per_scan: number;
    youtube_last_run: string | null;
    youtube_last_status: string;
    youtube_articles_today: number;
    auto_publish_enabled: boolean;
    auto_publish_min_quality: number;
    auto_publish_max_per_hour: number;
    auto_publish_max_per_day: number;
    auto_publish_require_image: boolean;
    auto_publish_require_safe_feed: boolean;
    auto_publish_as_draft: boolean;
    auto_publish_today_count: number;
    auto_publish_last_run: string | null;
    auto_image_mode: string;
    auto_image_prefer_press: boolean;
    auto_image_last_run: string | null;
    auto_image_last_status: string;
    auto_image_today_count: number;
    google_indexing_enabled: boolean;
    google_indexing_last_run: string | null;
    google_indexing_last_status: string;
    google_indexing_today_count: number;
    deep_specs_enabled: boolean;
    deep_specs_interval_hours: number;
    deep_specs_max_per_cycle: number;
    deep_specs_last_run: string | null;
    deep_specs_last_status: string;
    deep_specs_today_count: number;
    rss_lock: boolean;
    youtube_lock: boolean;
    auto_publish_lock: boolean;
    score_lock: boolean;
    deep_specs_lock: boolean;
    // Telegram
    telegram_enabled: boolean;
    telegram_channel_id: string;
    telegram_post_with_image: boolean;
    telegram_last_run: string | null;
    telegram_last_status: string;
    telegram_today_count: number;
}

export interface DecisionEntry {
    id: number;
    title: string;
    decision: string;
    reason: string;
    quality_score: number;
    safety_score: string;
    image_policy: string;
    feed_name: string;
    source_type: string;
    has_image: boolean;
    source_is_youtube: boolean;
    created_at: string;
}

export interface AutomationStats {
    pending_total: number;
    pending_high_quality: number;
    published_today: number;
    auto_published_today: number;
    rss_articles_today: number;
    youtube_articles_today: number;
    safety_overview: {
        safety_counts: { safe: number; review: number; unsafe: number };
        image_policy_counts: { original: number; pexels_only: number; pexels_fallback: number; unchecked: number };
        total_feeds: number;
    };
    eligible: {
        total: number;
        safe: number;
        review: number;
        unsafe: number;
    };
    recent_decisions: DecisionEntry[];
    decision_breakdown: Record<string, number>;
    total_decisions: number;
    recent_auto_published: Array<{
        id: number;
        title: string;
        quality_score: number;
        published_at: string;
    }>;
    ml_model?: {
        trained: boolean;
        article_count?: number;
        vocabulary_size?: number;
        unique_tags?: number;
        unique_categories?: number;
        built_at?: string;
        model_size_kb?: number;
    };
    enrichment_report?: {
        last_run: string;
        articles_processed: number;
        articles_total: number;
        errors: number;
        tags_created: number;
        tags_matched: number;
        duration_seconds: number;
        mode: string;
        // Fallback fields from older/alternative report formats
        current?: number;
        total?: number;
        elapsed_seconds?: number;
        error_count?: number;
        summary?: Record<string, unknown>;
    } | null;
    recent_social_posts?: SocialPostEntry[];
}

export interface SocialPostEntry {
    id: number;
    article_id: number;
    article_title: string;
    platform: string;
    status: string;
    external_id: string;
    error_message: string;
    posted_at: string | null;
    created_at: string;
}
