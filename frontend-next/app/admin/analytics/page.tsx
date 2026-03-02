'use client';

import OverallStats from '@/components/admin/analytics/OverallStats';
import AIEnrichmentStats from '@/components/admin/analytics/AIEnrichmentStats';
import AITopTags from '@/components/admin/analytics/AITopTags';
import AIGenerationQuality from '@/components/admin/analytics/AIGenerationQuality';
import PopularModels from '@/components/admin/analytics/PopularModels';
import AIProviderPerformance from '@/components/admin/analytics/AIProviderPerformance';
import GSCDashboard from '@/components/admin/analytics/GSCDashboard';
import EngagementDistribution from '@/components/admin/analytics/EngagementDistribution';
import TopArticlesTable from '@/components/admin/analytics/TopArticlesTable';
import ABTestsSection from '@/components/admin/analytics/ABTestsSection';
import MLHealthWidget from '@/components/admin/analytics/MLHealthWidget';
import ExtraStatsWidgets from '@/components/admin/analytics/ExtraStatsWidgets';

export default function AnalyticsPage() {
  return (
    <div className="space-y-10 pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-black text-gray-950">📊 Analytics Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">Real-time stats, AI insights, and Google Search performance</p>
      </div>

      {/* ═══════ Section 1: Site Overview ═══════ */}
      <section>
        <OverallStats />
      </section>

      {/* ═══════ Section 1.5: Platform Overview ═══════ */}
      <section className="space-y-6">
        <h2 className="text-xl font-bold text-gray-900 border-l-4 border-purple-600 pl-4">
          🔍 Platform Overview
          <span className="text-sm font-normal text-gray-400 ml-2">
            Subscribers, RSS feeds & system health
          </span>
        </h2>
        <ExtraStatsWidgets />
      </section>

      {/* ═══════ Section 2: Content & Engagement ═══════ */}
      <section className="space-y-6">
        <h2 className="text-xl font-bold text-gray-900 border-l-4 border-green-600 pl-4">
          📈 Content & Engagement
        </h2>
        <EngagementDistribution />
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <TopArticlesTable />
          <PopularModels />
        </div>
      </section>

      {/* ═══════ Section 3: ML Model Health ═══════ */}
      <section className="space-y-6">
        <h2 className="text-xl font-bold text-gray-900 border-l-4 border-cyan-600 pl-4">
          🧠 ML Model Health
          <span className="text-sm font-normal text-gray-400 ml-2">
            Maturity level and per-feature scores
          </span>
        </h2>
        <MLHealthWidget />
      </section>

      {/* ═══════ Section 4: AI Pipeline Health ═══════ */}
      <section className="space-y-6">
        <h2 className="text-xl font-bold text-gray-900 border-l-4 border-violet-600 pl-4">
          🤖 AI Pipeline Health
          <span className="text-sm font-normal text-gray-400 ml-2">
            How well AI enriches your content
          </span>
        </h2>
        <AIEnrichmentStats />
        <AITopTags />
      </section>

      {/* ═══════ Section 4: AI Generation Quality ═══════ */}
      <section>
        <AIGenerationQuality />
      </section>

      {/* ═══════ Section 5: AI Provider & SEO ═══════ */}
      <section className="space-y-6">
        <AIProviderPerformance />
        <GSCDashboard />
      </section>

      {/* ═══════ Section 6: A/B Tests ═══════ */}
      <section>
        <ABTestsSection />
      </section>
    </div>
  );
}
