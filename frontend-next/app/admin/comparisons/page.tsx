'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  GitCompareArrows, Search, Loader2, Sparkles,
  ChevronDown, Filter, RefreshCw, CheckCircle2, Eye,
  Clock, FileText, ExternalLink
} from 'lucide-react';
import api from '@/lib/api';
import Link from 'next/link';

interface SpecSummary {
  id: number;
  make: string;
  model_name: string;
  trim_name: string;
  body_type: string | null;
  body_type_display: string | null;
  fuel_type: string | null;
  fuel_type_display: string | null;
  power_hp: number | null;
  battery_kwh: number | null;
  range_wltp: number | null;
  range_km: number | null;
  price_from: number | null;
  price_to: number | null;
  currency: string | null;
  price_display: string;
  acceleration_0_100: number | null;
  image_url: string | null;
}

interface DataHealth {
  filled: number;
  total: number;
}

interface ExistingArticle {
  id: number;
  slug: string;
  is_published: boolean;
  title: string;
}

interface ComparisonPair {
  score: number;
  spec_a: SpecSummary;
  spec_b: SpecSummary;
  data_health: { a: DataHealth; b: DataHealth };
  existing_article: ExistingArticle | null;
  segment: string;
}

interface PairsResponse {
  total_vehicles: number;
  total_pairs: number;
  showing: number;
  segments: Record<string, number>;
  pairs: ComparisonPair[];
}

interface RecentComparison {
  id: number;
  title: string;
  slug: string;
  is_published: boolean;
  created_at: string | null;
  image_url: string | null;
  spec_a: string;
  spec_b: string;
  word_count: number;
  provider: string;
}

function HealthBar({ health }: { health: DataHealth }) {
  const pct = Math.round((health.filled / health.total) * 100);
  const color = pct >= 75 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-400';
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-gray-500 font-medium">{health.filled}/{health.total}</span>
    </div>
  );
}

function SpecBadge({ label, value, unit }: { label: string; value: number | null; unit?: string }) {
  if (value === null) return null;
  return (
    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-gray-100 rounded text-[10px] text-gray-600 font-medium">
      {label}: <strong className="text-gray-800">{typeof value === 'number' ? value.toLocaleString() : value}{unit || ''}</strong>
    </span>
  );
}

function formatTimeAgo(iso: string | null): string {
  if (!iso) return 'Unknown';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return 'Unknown';
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export default function ComparisonsPage() {
  const [data, setData] = useState<PairsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null); // "specAid-specBid"
  const [search, setSearch] = useState('');
  const [segmentFilter, setSegmentFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [provider, setProvider] = useState('gemini');
  const [limit, setLimit] = useState(30);
  const [generatedKeys, setGeneratedKeys] = useState<Set<string>>(new Set());

  // Active generation state (pinned card at top)
  const [activePair, setActivePair] = useState<ComparisonPair | null>(null);
  const [activeResult, setActiveResult] = useState<ExistingArticle | null>(null);

  // Recently generated comparisons (from backend)
  const [recentComparisons, setRecentComparisons] = useState<RecentComparison[]>([]);
  const [showRecent, setShowRecent] = useState(true);

  const fetchPairs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (segmentFilter) {
        const parts = segmentFilter.split(' ');
        if (parts.length >= 2) {
          params.set('fuel', parts[0]);
          params.set('segment', parts.slice(1).join(' '));
        }
      }
      params.set('limit', String(limit));
      const { data } = await api.get(`/vehicle-specs/comparison-pairs/?${params.toString()}`);
      setData(data);
    } catch (err) {
      console.error('Failed to fetch pairs:', err);
    }
    setLoading(false);
  }, [segmentFilter, limit]);

  const fetchRecentComparisons = useCallback(async () => {
    try {
      const { data } = await api.get('/vehicle-specs/recent-comparisons/');
      setRecentComparisons(data.articles || []);
    } catch (err) {
      console.error('Failed to fetch recent comparisons:', err);
    }
  }, []);

  useEffect(() => { fetchPairs(); fetchRecentComparisons(); }, [fetchPairs, fetchRecentComparisons]);

  const handleGenerate = async (pair: ComparisonPair) => {
    const key = `${pair.spec_a.id}-${pair.spec_b.id}`;
    setGenerating(key);
    setActivePair(pair);
    setActiveResult(null);

    // Scroll to top so user sees the pinned card
    window.scrollTo({ top: 0, behavior: 'smooth' });

    try {
      const { data: result } = await api.post('/vehicle-specs/generate-comparison/', {
        spec_a_id: pair.spec_a.id,
        spec_b_id: pair.spec_b.id,
        provider,
      });
      if (result.success) {
        const article: ExistingArticle = {
          id: result.article.id,
          slug: result.article.slug,
          is_published: false,
          title: result.article.title,
        };
        setActiveResult(article);
        // Remove from pairs list
        setGeneratedKeys(prev => new Set(prev).add(key));
        // Refresh recent comparisons
        fetchRecentComparisons();
      } else {
        alert(`Generation failed: ${result.error}`);
        setActivePair(null);
      }
    } catch (err) {
      console.error('Generation failed:', err);
      alert('Generation failed. Check console.');
      setActivePair(null);
    }
    setGenerating(null);
  };

  // Filter out already generated pairs
  const filteredPairs = (data?.pairs || []).filter(pair => {
    const key = `${pair.spec_a.id}-${pair.spec_b.id}`;
    if (generatedKeys.has(key)) return false;
    if (!search) return true;
    const q = search.toLowerCase();
    return pair.spec_a.make.toLowerCase().includes(q)
      || pair.spec_a.model_name.toLowerCase().includes(q)
      || pair.spec_b.make.toLowerCase().includes(q)
      || pair.spec_b.model_name.toLowerCase().includes(q);
  });

  const segments = Object.entries(data?.segments || {}).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <GitCompareArrows className="text-indigo-600" size={28} />
            Comparison Curator
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Generate &quot;X vs Y&quot; comparison articles from vehicle specs
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-1.5 px-3 py-2 border rounded-xl text-sm font-medium transition-colors ${
              showFilters ? 'bg-indigo-50 border-indigo-300 text-indigo-700' : 'border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            <Filter size={15} /> Filters
          </button>
          <button onClick={() => { fetchPairs(); fetchRecentComparisons(); }} disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 border border-gray-200 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50">
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search brands..."
              className="pl-10 pr-4 py-2 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 w-48" />
          </div>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="bg-white/80 backdrop-blur border border-gray-200 rounded-xl p-4 flex flex-wrap items-center gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Segment</label>
            <select value={segmentFilter} onChange={e => setSegmentFilter(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-indigo-500 text-gray-900">
              <option value="">All Segments</option>
              {segments.map(([seg, count]) => (
                <option key={seg} value={seg}>{seg} ({count})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">AI Provider</label>
            <select value={provider} onChange={e => setProvider(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-indigo-500 text-gray-900">
              <option value="gemini">Gemini</option>
              <option value="groq">Groq (Free)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">Show pairs</label>
            <select value={limit} onChange={e => setLimit(Number(e.target.value))}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-indigo-500 text-gray-900">
              <option value={15}>15</option>
              <option value={30}>30</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════
          PINNED: Active Generation Card
         ══════════════════════════════════════════════ */}
      {activePair && (
        <div className={`border-2 rounded-xl shadow-lg overflow-hidden transition-all ${
          generating ? 'border-indigo-400 bg-indigo-50/50 animate-pulse' : 'border-green-400 bg-green-50/50'
        }`}>
          <div className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white flex items-center gap-2">
            {generating ? (
              <><Loader2 size={14} className="animate-spin" /> Generating comparison...</>
            ) : (
              <><CheckCircle2 size={14} /> Comparison generated!</>
            )}
          </div>
          <div className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="font-bold text-gray-900">
                  {activePair.spec_a.make} {activePair.spec_a.model_name}
                </div>
                <span className="text-xs font-black text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded">VS</span>
                <div className="font-bold text-gray-900">
                  {activePair.spec_b.make} {activePair.spec_b.model_name}
                </div>
              </div>
              {activeResult && (
                <div className="flex items-center gap-2">
                  <Link href={`/admin/articles/${activeResult.id}/edit`}
                    className="flex items-center gap-1 px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-xs font-semibold hover:bg-green-200 transition-colors">
                    <FileText size={13} /> Edit Draft
                  </Link>
                  <Link href={`/articles/${activeResult.slug}`} target="_blank"
                    className="flex items-center gap-1 px-3 py-1.5 bg-indigo-100 text-indigo-700 rounded-lg text-xs font-semibold hover:bg-indigo-200 transition-colors">
                    <ExternalLink size={13} /> Preview
                  </Link>
                  <button onClick={() => { setActivePair(null); setActiveResult(null); }}
                    className="text-xs text-gray-400 hover:text-gray-600 ml-2">✕ Close</button>
                </div>
              )}
            </div>
            {activeResult && (
              <div className="mt-2 text-sm text-gray-600">
                📝 <strong>{activeResult.title}</strong>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════
          Recently Generated Comparisons
         ══════════════════════════════════════════════ */}
      {recentComparisons.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
          <button onClick={() => setShowRecent(!showRecent)}
            className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors">
            <div className="flex items-center gap-2">
              <Clock size={16} className="text-indigo-600" />
              <span className="font-bold text-gray-900 text-sm">Recently Generated</span>
              <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full font-medium">
                {recentComparisons.length}
              </span>
            </div>
            <ChevronDown size={16} className={`text-gray-400 transition-transform ${showRecent ? 'rotate-180' : ''}`} />
          </button>
          {showRecent && (
            <div className="border-t border-gray-100 divide-y divide-gray-50 max-h-[300px] overflow-y-auto">
              {recentComparisons.map((comp) => (
                <div key={comp.id} className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors">
                  {comp.image_url ? (
                    <img src={comp.image_url} alt="" className="w-10 h-10 rounded-lg object-cover flex-shrink-0 border border-gray-200" />
                  ) : (
                    <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-xs flex-shrink-0">
                      VS
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-gray-900 truncate">{comp.spec_a} vs {comp.spec_b}</div>
                    <div className="text-xs text-gray-400 flex items-center gap-2">
                      <span>{formatTimeAgo(comp.created_at)}</span>
                      <span>·</span>
                      <span>{comp.word_count} words</span>
                      {comp.provider && <><span>·</span><span className="capitalize">{comp.provider}</span></>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      comp.is_published
                        ? 'bg-green-100 text-green-700 border border-green-200'
                        : 'bg-amber-100 text-amber-700 border border-amber-200'
                    }`}>
                      {comp.is_published ? '✅ Published' : '📝 Draft'}
                    </span>
                    <Link href={`/admin/articles/${comp.id}/edit`}
                      className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">
                      Edit
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Stats */}
      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm">
            <div className="text-2xl font-bold text-gray-900">{data.total_vehicles}</div>
            <div className="text-xs text-gray-500 font-medium">Vehicles with data</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm">
            <div className="text-2xl font-bold text-indigo-600">{data.total_pairs}</div>
            <div className="text-xs text-gray-500 font-medium">Possible pairs</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm">
            <div className="text-2xl font-bold text-purple-600">{segments.length}</div>
            <div className="text-xs text-gray-500 font-medium">Segments</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm">
            <div className="text-2xl font-bold text-green-600">{recentComparisons.length}</div>
            <div className="text-xs text-gray-500 font-medium">Generated</div>
          </div>
        </div>
      )}

      {/* Segment Tags */}
      {segments.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button onClick={() => setSegmentFilter('')}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
              !segmentFilter ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}>
            All
          </button>
          {segments.map(([seg, count]) => (
            <button key={seg} onClick={() => setSegmentFilter(seg === segmentFilter ? '' : seg)}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                seg === segmentFilter ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}>
              {seg} <span className="opacity-70">({count})</span>
            </button>
          ))}
        </div>
      )}

      {/* Pairs List */}
      <div className="space-y-3">
        {loading ? (
          <div className="flex items-center justify-center py-20 text-gray-400">
            <Loader2 size={28} className="animate-spin mr-3" /> Loading pairs...
          </div>
        ) : filteredPairs.length === 0 ? (
          <div className="text-center py-20 text-gray-400">
            No comparison pairs found. Need at least 2 vehicles with body_type and fuel_type in VehicleSpecs.
          </div>
        ) : (
          filteredPairs.map((pair) => {
            const key = `${pair.spec_a.id}-${pair.spec_b.id}`;
            const isGenerating = generating === key;
            const existingArticle = pair.existing_article;
            const healthA = pair.data_health.a;
            const healthB = pair.data_health.b;
            const avgHealth = Math.round(((healthA.filled + healthB.filled) / (healthA.total + healthB.total)) * 100);

            return (
              <div key={key} className={`bg-white border rounded-xl shadow-sm overflow-hidden transition-all hover:shadow-md ${
                existingArticle ? 'border-green-200 bg-green-50/30' : 'border-gray-200'
              }`}>
                <div className="flex items-stretch">
                  {/* Score badge */}
                  <div className={`flex flex-col items-center justify-center px-4 border-r ${
                    pair.score >= 25 ? 'bg-gradient-to-b from-green-500 to-emerald-600 text-white' :
                    pair.score >= 18 ? 'bg-gradient-to-b from-yellow-400 to-amber-500 text-white' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    <div className="text-lg font-bold">{pair.score}</div>
                    <div className="text-[9px] uppercase tracking-wider font-semibold opacity-80">Score</div>
                  </div>

                  {/* Car A */}
                  <div className="flex-1 p-4 border-r border-dashed border-gray-200">
                    <div className="flex items-start gap-3">
                      {pair.spec_a.image_url ? (
                        <img src={pair.spec_a.image_url} alt={`${pair.spec_a.make} ${pair.spec_a.model_name}`}
                          className="w-12 h-12 rounded-lg object-cover flex-shrink-0 border border-gray-200" />
                      ) : (
                        <div className="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center text-gray-400 font-bold text-sm flex-shrink-0 border border-gray-200">
                          {pair.spec_a.make.charAt(0)}
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="font-bold text-gray-900">{pair.spec_a.make}</div>
                            <div className="text-sm text-gray-600">{pair.spec_a.model_name}</div>
                            {pair.spec_a.trim_name && (
                              <div className="text-xs text-gray-400">{pair.spec_a.trim_name}</div>
                            )}
                          </div>
                          <HealthBar health={healthA} />
                        </div>
                        <div className="flex flex-wrap gap-1 mt-2">
                          <SpecBadge label="HP" value={pair.spec_a.power_hp} />
                          <SpecBadge label="Range" value={pair.spec_a.range_wltp || pair.spec_a.range_km} unit=" km" />
                          {pair.spec_a.price_display !== 'N/A' && (
                            <span className="inline-flex px-1.5 py-0.5 bg-green-50 border border-green-200 rounded text-[10px] text-green-700 font-medium">
                              {pair.spec_a.price_display}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* VS */}
                  <div className="flex items-center px-3">
                    <div className="bg-gradient-to-b from-indigo-500 to-purple-600 text-white text-xs font-black px-2.5 py-1.5 rounded-lg">
                      VS
                    </div>
                  </div>

                  {/* Car B */}
                  <div className="flex-1 p-4 border-l border-dashed border-gray-200">
                    <div className="flex items-start gap-3">
                      {pair.spec_b.image_url ? (
                        <img src={pair.spec_b.image_url} alt={`${pair.spec_b.make} ${pair.spec_b.model_name}`}
                          className="w-12 h-12 rounded-lg object-cover flex-shrink-0 border border-gray-200" />
                      ) : (
                        <div className="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center text-gray-400 font-bold text-sm flex-shrink-0 border border-gray-200">
                          {pair.spec_b.make.charAt(0)}
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="font-bold text-gray-900">{pair.spec_b.make}</div>
                            <div className="text-sm text-gray-600">{pair.spec_b.model_name}</div>
                            {pair.spec_b.trim_name && (
                              <div className="text-xs text-gray-400">{pair.spec_b.trim_name}</div>
                            )}
                          </div>
                          <HealthBar health={healthB} />
                        </div>
                        <div className="flex flex-wrap gap-1 mt-2">
                          <SpecBadge label="HP" value={pair.spec_b.power_hp} />
                          <SpecBadge label="Range" value={pair.spec_b.range_wltp || pair.spec_b.range_km} unit=" km" />
                          {pair.spec_b.price_display !== 'N/A' && (
                            <span className="inline-flex px-1.5 py-0.5 bg-green-50 border border-green-200 rounded text-[10px] text-green-700 font-medium">
                              {pair.spec_b.price_display}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col items-center justify-center gap-2 px-4 bg-gray-50/50 border-l border-gray-200">
                    {existingArticle ? (
                      <>
                        <Link href={`/admin/articles/${existingArticle.id}/edit`}
                          className="flex items-center gap-1 px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-xs font-semibold hover:bg-green-200 transition-colors">
                          <CheckCircle2 size={13} />
                          {existingArticle.is_published ? 'Published' : 'Draft'}
                        </Link>
                        <Link href={`/articles/${existingArticle.slug}`} target="_blank"
                          className="flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600 transition-colors">
                          <Eye size={12} /> View
                        </Link>
                      </>
                    ) : (
                      <button onClick={() => handleGenerate(pair)} disabled={isGenerating || generating !== null}
                        className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-sm">
                        {isGenerating ? (
                          <><Loader2 size={13} className="animate-spin" /> Generating...</>
                        ) : (
                          <><Sparkles size={13} /> Generate</>
                        )}
                      </button>
                    )}
                    <span className={`text-[10px] font-medium ${
                      avgHealth >= 75 ? 'text-green-600' : avgHealth >= 50 ? 'text-yellow-600' : 'text-red-500'
                    }`}>
                      {avgHealth >= 75 ? '✅' : avgHealth >= 50 ? '⚠️' : '❌'} {avgHealth}% data
                    </span>
                  </div>
                </div>

                {/* Segment tag */}
                <div className="flex items-center justify-between px-4 py-1.5 bg-gray-50 border-t border-gray-100">
                  <span className="inline-flex px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full text-[10px] font-semibold">
                    {pair.segment}
                  </span>
                  <span className="text-[10px] text-gray-400">
                    #{pair.spec_a.id} vs #{pair.spec_b.id}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Load more hint */}
      {data && data.total_pairs > data.showing && (
        <div className="text-center py-4">
          <button onClick={() => setLimit(prev => prev + 30)}
            className="flex items-center gap-2 mx-auto px-4 py-2 bg-gray-100 text-gray-600 rounded-xl text-sm font-medium hover:bg-gray-200 transition-colors">
            <ChevronDown size={16} />
            Show more ({data.total_pairs - data.showing} remaining)
          </button>
        </div>
      )}
    </div>
  );
}
