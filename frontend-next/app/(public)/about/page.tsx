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
          {/* Custom Content from Admin — shows as additional block if set */}
          {hasCustomContent && (
            <section className="bg-white rounded-2xl shadow-lg p-8 md:p-12 mb-8">
              <div
                className="prose prose-lg max-w-none text-gray-700"
                dangerouslySetInnerHTML={{ __html: sanitizeHtml(pageContent) }}
              />
            </section>
          )}

          {/* Meet the Founder — always at the top */}
          <section className="bg-gradient-to-br from-slate-900 via-purple-900 to-gray-900 rounded-2xl shadow-xl p-8 md:p-12 mb-8 text-white">
            <h2 className="text-3xl font-black mb-8 text-center">Meet the Founder</h2>
            <div className="flex flex-col md:flex-row items-center md:items-start gap-8">
              <div className="flex-shrink-0">
                <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-purple-400 shadow-xl">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="/alex-sostin.jpg"
                    alt="Alexander Sostin — Founder of Fresh Motors"
                    className="w-full h-full object-cover object-[center_15%]"
                  />
                </div>
              </div>
              <div className="flex-1">
                <div className="mb-1">
                  <span className="text-2xl font-black text-white">Alexander Sostin</span>
                </div>
                <p className="text-purple-300 text-sm mb-5">29 · Rishon LeZion, Israel · Founder &amp; Editor</p>
                <p className="text-gray-300 mb-4 leading-relaxed">
                  I&apos;ve always been obsessed with cars — the engineering, the design, the way they keep evolving.
                  Every car on the planet tells a story about the people who built it and the market it was built for.
                  But alongside that passion, I&apos;m also into cycling, football, ping pong, gaming, and animals.
                </p>
                <p className="text-gray-300 mb-4 leading-relaxed">
                  When I&apos;m not doing any of that, I program. I love building things from scratch — which is exactly
                  how Fresh Motors came to life. In late 2025 I started building it, and by early 2026 it had grown
                  into a real platform — covering the global automotive world honestly
                  and in depth: from German engineering to Japanese reliability to the EV revolution coming out of China —
                  all the cars that matter, wherever they come from.
                </p>
                <p className="text-gray-300 mb-6 leading-relaxed">
                  This site is a work in progress — I&apos;m constantly improving it, and your readership and feedback
                  genuinely help shape it. Thanks for being here.
                </p>
                <a
                  href="mailto:info@freshmotors.net"
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl font-semibold transition-colors text-sm"
                >
                  📧 info@freshmotors.net
                </a>
              </div>
            </div>
          </section>

          {/* Our Story */}
          <section className="bg-white rounded-2xl shadow-lg p-8 md:p-12 mb-8">
            <h2 className="text-3xl font-black text-gray-900 mb-6">Our Story</h2>
            <div className="prose prose-lg max-w-none text-gray-700">
              <p className="mb-4">
                Fresh Motors was launched in late 2025 by Alex Sostin, an automotive enthusiast with a passion for the entire global car industry. What started as a personal project at the start of 2026 to track the rapidly evolving EV market — especially brands overlooked by Western media — has grown into a daily news platform covering cars from every major manufacturer worldwide.
              </p>
              <p className="mb-4">
                We cover everything that moves: from BYD and Zeekr to BMW and Toyota, from supercar launches to budget city EVs. Our particular strength is covering brands that rarely make headlines outside their home markets — Chinese, Korean, and emerging manufacturers reshaping what modern cars look like and cost. Our readers are automotive professionals, enthusiasts, and informed buyers who want facts, not press releases.
              </p>
              <p>
                Every article on Fresh Motors is editorially reviewed before publication. We cross-reference manufacturer specifications with independent test data, and we clearly label when information is confirmed versus reported. We believe automotive journalism should be honest about what it knows and what it doesn&apos;t.
              </p>
            </div>
          </section>

          {/* Editorial Approach */}
          <section className="bg-white rounded-2xl shadow-lg p-8 md:p-12 mb-8">
            <h2 className="text-3xl font-black text-gray-900 mb-6">Our Editorial Approach</h2>
            <div className="prose prose-lg max-w-none text-gray-700">
              <p className="mb-4">
                Fresh Motors uses AI-assisted research tools to monitor global automotive news and compile technical specifications from manufacturer announcements, press releases, and international automotive media. All content is reviewed editorially before publication to ensure accuracy and relevance.
              </p>
              <p className="mb-4">
                We distinguish clearly between <strong>confirmed specifications</strong> (from official manufacturer sources) and <strong>expected or reported figures</strong> (from credible third-party coverage). We never publish fabricated specs or guessed performance numbers.
              </p>
              <p>
                Our focus is on providing useful, data-driven content for readers making real decisions — whether that&apos;s understanding a powertrain architecture, comparing range across competing vehicles, or tracking pricing trends across global markets.
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
                  We verify specs against official sources and flag anything that isn&apos;t confirmed.
                </p>
              </div>

              <div className="bg-white rounded-xl shadow-md p-6 text-center hover:shadow-xl transition-shadow">
                <div className="bg-indigo-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <TrendingUp className="text-indigo-600" size={32} />
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">Global Coverage</h3>
                <p className="text-gray-600">
                  Every car on the planet deserves coverage — from legacy European brands to emerging Chinese EV makers.
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
                <h3 className="text-xl font-bold text-purple-600 mb-3">Global New Models</h3>
                <p className="text-gray-700 mb-4">
                  Launch coverage of every significant new car release worldwide — from Toyota and BMW to BYD, Zeekr, and the emerging brands reshaping the industry.
                </p>
              </div>
              <div>
                <h3 className="text-xl font-bold text-purple-600 mb-3">Technical Specifications</h3>
                <p className="text-gray-700 mb-4">
                  Detailed powertrain breakdowns, battery chemistry, charging architecture, ADAS hardware — the specs that matter for real-world decisions.
                </p>
              </div>
              <div>
                <h3 className="text-xl font-bold text-purple-600 mb-3">Market &amp; Pricing</h3>
                <p className="text-gray-700 mb-4">
                  Launch pricing across global markets with context on how trade dynamics, tariffs, and local competition affect what you actually pay.
                </p>
              </div>
              <div>
                <h3 className="text-xl font-bold text-purple-600 mb-3">Industry Analysis</h3>
                <p className="text-gray-700 mb-4">
                  Brand strategy, platform evolution, competitive positioning — understanding the bigger picture behind every car release.
                </p>
              </div>
            </div>
          </section>

        </div>
      </main >

    </>
  );
}
