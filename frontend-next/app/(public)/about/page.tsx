'use client';

import { useState, useEffect } from 'react';
import { Users, Target, Award, TrendingUp, Loader2 } from 'lucide-react';
import { getApiUrl } from '@/lib/api';
import { sanitizeHtml } from '@/lib/sanitize';

interface SiteSettings {
  about_page_title: string;
  about_page_content: string;
  about_page_enabled: boolean;
}



export default function AboutPage() {
  const [settings, setSettings] = useState<SiteSettings | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const apiUrl = getApiUrl();
      const response = await fetch(`${apiUrl}/settings/`);
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  };

  // Get content - use API content if available, otherwise use default
  const pageTitle = settings?.about_page_title || 'About Fresh Motors';
  const pageContent = settings?.about_page_content || '';
  const hasCustomContent = pageContent.trim().length > 0;

  if (loading) {
    return (
      <main className="flex-1 bg-gray-50 flex items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-purple-600" size={48} />
      </main>
    );
  }

  return (
    <>

      <main className="flex-1 bg-gray-50">
        {/* Hero Section */}
        <div className="bg-gradient-to-r from-slate-900 via-purple-900 to-gray-900 text-white py-20">
          <div className="container mx-auto px-4 text-center">
            <h1 className="text-4xl md:text-5xl font-black mb-4">{pageTitle}</h1>
            <p className="text-xl text-gray-300 max-w-3xl mx-auto">
              Your trusted source for the latest automotive news, in-depth reviews, and expert insights.
            </p>
          </div>
        </div>

        <div className="container mx-auto px-4 py-12">
          {/* Custom Content from Admin */}
          {hasCustomContent ? (
            <section className="bg-white rounded-2xl shadow-lg p-8 md:p-12 mb-8">
              <div
                className="prose prose-lg max-w-none text-gray-700"
                dangerouslySetInnerHTML={{ __html: sanitizeHtml(pageContent) }}
              />
            </section>
          ) : (
            <>
              {/* Our Story */}
              <section className="bg-white rounded-2xl shadow-lg p-8 md:p-12 mb-8">
                <h2 className="text-3xl font-black text-gray-900 mb-6">Our Story</h2>
                <div className="prose prose-lg max-w-none text-gray-700">
                  <p className="mb-4">
                    Fresh Motors was founded in 2024 by Alex Sostin, an automotive enthusiast with a focus on the rapidly evolving global EV market. What started as a personal mission to cover the Chinese electric vehicle revolution — largely ignored by Western automotive media — has grown into a daily news platform tracking over 30 brands across 20+ markets.
                  </p>
                  <p className="mb-4">
                    We specialise in cars that rarely make headlines outside their home markets: BYD, NIO, ZEEKR, AITO, XPENG, Xiaomi, and dozens of other manufacturers reshaping what affordable, technology-rich motoring looks like. Our readers are automotive professionals, EV enthusiasts, and informed buyers who want facts — not hype.
                  </p>
                  <p>
                    Every article on Fresh Motors is editorially reviewed before publication. We cross-reference manufacturer specifications with independent test data, and we clearly label when information is confirmed versus expected. We believe automotive journalism should be honest about what it knows and what it doesn't.
                  </p>
                </div>
              </section>

              {/* Editorial Approach */}
              <section className="bg-white rounded-2xl shadow-lg p-8 md:p-12 mb-8">
                <h2 className="text-3xl font-black text-gray-900 mb-6">Our Editorial Approach</h2>
                <div className="prose prose-lg max-w-none text-gray-700">
                  <p className="mb-4">
                    Fresh Motors uses AI-assisted research tools to monitor global automotive news and compile technical specifications from manufacturer announcements, press releases, and international automotive media. All content is reviewed by our editorial team before publication to ensure accuracy and relevance.
                  </p>
                  <p className="mb-4">
                    We distinguish clearly between <strong>confirmed specifications</strong> (from official manufacturer sources) and <strong>expected or reported figures</strong> (from credible third-party coverage). We never publish fabricated specs or guessed performance numbers.
                  </p>
                  <p>
                    Our focus is on providing useful, data-driven content for readers making real decisions — whether that's understanding a new model's powertrain architecture, comparing range across competing vehicles, or tracking pricing trends in key markets.
                  </p>
                </div>
              </section>

              {/* Values */}
              <section className="mb-8">
                <h2 className="text-3xl font-black text-gray-900 mb-6 text-center">What We Stand For</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div className="bg-white rounded-xl shadow-md p-6 text-center hover:shadow-xl transition-shadow">
                    <div className="bg-purple-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Target className="text-purple-600" size={32} />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Accuracy First</h3>
                    <p className="text-gray-600">
                      We verify specs against official sources and flag anything that isn't confirmed.
                    </p>
                  </div>

                  <div className="bg-white rounded-xl shadow-md p-6 text-center hover:shadow-xl transition-shadow">
                    <div className="bg-indigo-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                      <TrendingUp className="text-indigo-600" size={32} />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Global Coverage</h3>
                    <p className="text-gray-600">
                      We cover brands and markets that most Western auto media ignores, especially Chinese EVs.
                    </p>
                  </div>

                  <div className="bg-white rounded-xl shadow-md p-6 text-center hover:shadow-xl transition-shadow">
                    <div className="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Award className="text-blue-600" size={32} />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Editorial Integrity</h3>
                    <p className="text-gray-600">
                      No sponsored content posing as editorial. No undisclosed affiliate arrangements.
                    </p>
                  </div>

                  <div className="bg-white rounded-xl shadow-md p-6 text-center hover:shadow-xl transition-shadow">
                    <div className="bg-green-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Users className="text-green-600" size={32} />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Reader-Focused</h3>
                    <p className="text-gray-600">
                      We write for buyers, enthusiasts, and industry professionals — not clicks.
                    </p>
                  </div>
                </div>
              </section>

              {/* What We Cover */}
              <section className="bg-white rounded-2xl shadow-lg p-8 md:p-12">
                <h2 className="text-3xl font-black text-gray-900 mb-6">What We Cover</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h3 className="text-xl font-bold text-purple-600 mb-3">Chinese Electric Vehicles</h3>
                    <p className="text-gray-700 mb-4">
                      In-depth coverage of BYD, NIO, ZEEKR, AITO, XPENG, Chery, Geely, Dongfeng, and 20+ other manufacturers — including models not yet launched in Western markets.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-purple-600 mb-3">Technical Specifications</h3>
                    <p className="text-gray-700 mb-4">
                      Detailed powertrain breakdowns, battery chemistry analysis, charging architecture, ADAS hardware — the specs that matter for real-world ownership.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-purple-600 mb-3">Market & Pricing</h3>
                    <p className="text-gray-700 mb-4">
                      Launch pricing across CNY, EUR, AUD and other markets, with coverage of how global tariffs and trade dynamics affect EV pricing internationally.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-purple-600 mb-3">Industry Analysis</h3>
                    <p className="text-gray-700 mb-4">
                      Brand strategy, model lineup evolution, technology platform changes, and competitive positioning across the global EV landscape.
                    </p>
                  </div>
                </div>
              </section>
            </>
          )}
        </div>
      </main>

    </>
  );
}
