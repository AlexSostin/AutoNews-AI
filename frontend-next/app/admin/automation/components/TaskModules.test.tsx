import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { TaskModules } from './TaskModules';
import { AutomationSettings, AutomationStats } from '../types';

describe('TaskModules Component', () => {
    const defaultSettings = {
        rss_scan_enabled: true,
        rss_scan_interval_minutes: 60,
        rss_max_articles_per_scan: 10,
        youtube_scan_enabled: false,
        youtube_scan_interval_minutes: 120,
        youtube_max_videos_per_scan: 3,
        auto_publish_enabled: true,
        auto_publish_min_quality: 7,
        auto_publish_max_per_hour: 5,
        auto_publish_max_per_day: 50,
        auto_publish_require_image: true,
        auto_publish_require_safe_feed: true,
        auto_publish_as_draft: false,
        auto_image_mode: 'search_first',
        auto_image_prefer_press: true,
        telegram_enabled: true,
        telegram_post_with_image: true,
        google_indexing_enabled: true,
        deep_specs_enabled: true,
        deep_specs_interval_hours: 6,
        deep_specs_max_per_cycle: 5,
        comparison_enabled: true,
        comparison_max_per_week: 2,
    } as AutomationSettings;

    const defaultStats = {
        eligible: { total: 100, safe: 80, review: 15, unsafe: 5 },
        ml_model: {
            trained: true,
            built_at: new Date().toISOString(),
            article_count: 5000,
            unique_tags: 1500,
            vocabulary_size: 25000,
        },
        enrichment_report: null,
        recent_social_posts: [],
    } as unknown as AutomationStats;

    it('renders all key automation modules', () => {
        render(
            <TaskModules
                settings={defaultSettings}
                stats={defaultStats}
                eligibleStats={defaultStats.eligible}
                saving={false}
                triggering={null}
                updateSetting={vi.fn()}
                triggerTask={vi.fn()}
            />
        );

        // Check for presence of module titles
        expect(screen.getByText('📡 RSS Scanning')).toBeInTheDocument();
        expect(screen.getByText('🎬 YouTube Scanning')).toBeInTheDocument();
        expect(screen.getByText('📝 Auto-Publish')).toBeInTheDocument();
        expect(screen.getByText('📸 Auto-Image (AI)')).toBeInTheDocument();
        expect(screen.getByText('🚗 VehicleSpecs Cards')).toBeInTheDocument();
        expect(screen.getByText('🆚 Comparison Articles')).toBeInTheDocument();
        expect(screen.getByText('📱 Telegram Publishing')).toBeInTheDocument();
        expect(screen.getByText('📊 Quality Scoring')).toBeInTheDocument();
        expect(screen.getByText('🧠 ML Content Recommender')).toBeInTheDocument();
        expect(screen.getByText('📦 Bulk Enrichment')).toBeInTheDocument();
        expect(screen.getByText('🧹 A/B Test Lifecycle')).toBeInTheDocument();
    });

    it('calls triggerTask when action buttons are clicked', () => {
        const triggerTaskMock = vi.fn();
        render(
            <TaskModules
                settings={defaultSettings}
                stats={defaultStats}
                eligibleStats={defaultStats.eligible}
                saving={false}
                triggering={null}
                updateSetting={vi.fn()}
                triggerTask={triggerTaskMock}
            />
        );

        // Quality Scoring manual trigger
        const scoreButton = screen.getByText('🔄 Score Unscored');
        fireEvent.click(scoreButton);
        expect(triggerTaskMock).toHaveBeenCalledWith('score');

        // ML Retrain manual trigger
        const retrainButton = screen.getByText('🔄 Retrain Now');
        fireEvent.click(retrainButton);
        expect(triggerTaskMock).toHaveBeenCalledWith('ml-retrain');
    });

    it('disables buttons while triggering is active', () => {
        render(
            <TaskModules
                settings={defaultSettings}
                stats={defaultStats}
                eligibleStats={defaultStats.eligible}
                saving={false}
                triggering="score" // Simulate scoring is running
                updateSetting={vi.fn()}
                triggerTask={vi.fn()}
            />
        );

        // The button should now say "Scoring..." and be disabled
        const inactiveScoreButton = screen.getByText('⏳ Scoring...');
        expect(inactiveScoreButton).toBeDisabled();
        
        // ML retrain button should still be enabled
        const retrainButton = screen.getByText('🔄 Retrain Now');
        expect(retrainButton).not.toBeDisabled();
    });
});
