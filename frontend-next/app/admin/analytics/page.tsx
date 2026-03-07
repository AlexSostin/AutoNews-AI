'use client';

import OverallStats from '@/components/admin/analytics/OverallStats';
import ReaderEngagementWidget from '@/components/admin/analytics/ReaderEngagementWidget';
import CapsuleFeedbackWidget from '@/components/admin/analytics/CapsuleFeedbackWidget';
import ArticleComplaintsWidget from '@/components/admin/analytics/ArticleComplaintsWidget';
import EngagementDistribution from '@/components/admin/analytics/EngagementDistribution';
import TopArticlesTable from '@/components/admin/analytics/TopArticlesTable';
import PopularModels from '@/components/admin/analytics/PopularModels';
import MLHealthWidget from '@/components/admin/analytics/MLHealthWidget';
import AIEnrichmentStats from '@/components/admin/analytics/AIEnrichmentStats';
import AITopTags from '@/components/admin/analytics/AITopTags';
import AIGenerationQuality from '@/components/admin/analytics/AIGenerationQuality';
import AIProviderPerformance from '@/components/admin/analytics/AIProviderPerformance';
import GSCDashboard from '@/components/admin/analytics/GSCDashboard';
import ABTestsSection from '@/components/admin/analytics/ABTestsSection';
import ExtraStatsWidgets from '@/components/admin/analytics/ExtraStatsWidgets';

function SectionHeader({ emoji, title, subtitle, color }: { emoji: string; title: string; subtitle?: string; color: string }) {
  return (
    <h2 className={`text-xl font-bold text-gray-900 border-l-4 ${color} pl-4`}>
      {emoji} {title}
      {subtitle && <span className="text-sm font-normal text-gray-400 ml-2">{subtitle}</span>}
    </h2>
  );
}

export default function AnalyticsPage() {
  return (
    <div className="space-y-10 pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-black text-gray-950">📊 Analytics Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">Real-time stats, reader engagement, AI insights & SEO performance</p>
      </div>

      {/* ═══ 1. Site Overview — headline numbers ═══ */}
      <section>
        <OverallStats />
      </section>

      {/* ═══ 2. Reader Quality — most valuable data ═══ */}
      <section className="space-y-6">
        <SectionHeader emoji="📖" title="Reader Quality" subtitle="Dwell time, scroll depth & feedback from real sessions" color="border-emerald-500" />
        {/* Full-width reader engagement (dwell + funnel + top articles) */}
        <ReaderEngagementWidget />
        {/* Two smaller widgets side by side */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <CapsuleFeedbackWidget />
          <ArticleComplaintsWidget />
        </div>
      </section>

      {/* ═══ 3. Content & Engagement — publication & views ═══ */}
      <section className="space-y-6">
        <SectionHeader emoji="📈" title="Content & Engagement" color="border-blue-500" />
        <EngagementDistribution />
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <TopArticlesTable />
          <PopularModels />
        </div>
      </section>

      {/* ═══ 4. ML Model Health ═══ */}
      <section className="space-y-6">
        <SectionHeader emoji="🧠" title="ML Model Health" subtitle="Maturity level and per-feature scores" color="border-cyan-500" />
        <MLHealthWidget />
      </section>

      {/* ═══ 5. AI Pipeline — enrichment & generation quality ═══ */}
      <section className="space-y-6">
        <SectionHeader emoji="🤖" title="AI Pipeline Health" subtitle="How well AI enriches your content" color="border-violet-600" />
        <AIEnrichmentStats />
        <AITopTags />
        <AIGenerationQuality />
        <AIProviderPerformance />
      </section>

      {/* ═══ 6. SEO — Google Search Console ═══ */}
      <section className="space-y-6">
        <SectionHeader emoji="🔍" title="SEO — Google Search Console" color="border-amber-500" />
        <GSCDashboard />
      </section>

      {/* ═══ 7. A/B Tests ═══ */}
      <section className="space-y-6">
        <SectionHeader emoji="🧪" title="A/B Tests" subtitle="Title & image variant performance" color="border-pink-500" />
        <ABTestsSection />
      </section>

      {/* ═══ 8. Platform Overview — system health, RSS, subscribers ═══ */}
      <section className="space-y-6">
        <SectionHeader emoji="⚙️" title="Platform Overview" subtitle="Subscribers, RSS feeds & system health" color="border-gray-400" />
        <ExtraStatsWidgets />
      </section>
    </div>
  );
}
