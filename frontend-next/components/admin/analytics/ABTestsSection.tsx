'use client';

import { useState } from 'react';
import useSWR from 'swr';
import { FlaskConical, Eye, Trophy, MousePointerClick, ArrowDown } from 'lucide-react';
import api from '@/lib/api';
import { ABTest } from '@/types/analytics';

interface ABRes {
    tests: ABTest[];
    count: number;
    active_count: number;
    winners_count: number;
}

const fetcher = (url: string) => api.get(url).then(res => res.data);

export default function ABTestsSection() {
    const [abTestPage, setAbTestPage] = useState(1);
    const { data: abRes, isLoading } = useSWR<ABRes>('/ab/tests/?limit=1000', fetcher, { keepPreviousData: true });

    if (isLoading) {
        return (
            <div className="space-y-6 mt-12 animate-pulse">
                <div className="h-8 w-64 bg-gray-200 rounded mb-6"></div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 h-[90px]"></div>
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 h-[90px]"></div>
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 h-[90px]"></div>
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-[400px]"></div>
            </div>
        );
    }

    if (!abRes || !abRes.tests || abRes.tests.length === 0) return null;

    const abTests = abRes.tests;
    const abItemsPerPage = 10;
    const totalAbPages = Math.ceil(abTests.length / abItemsPerPage);
    const paginatedAbTests = abTests.slice((abTestPage - 1) * abItemsPerPage, abTestPage * abItemsPerPage);

    return (
        <div className="space-y-6">
            <h2 className="text-xl font-bold text-gray-900 border-l-4 border-emerald-500 pl-4 mt-12">🧪 A/B Title Tests <span className="text-sm font-normal text-gray-400">({abTests.length} tests loaded)</span></h2>

            {/* Summary cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                    <div className="flex items-center gap-3">
                        <div className="bg-emerald-100 p-2.5 rounded-lg"><FlaskConical className="text-emerald-600" size={20} /></div>
                        <div>
                            <p className="text-2xl font-black text-gray-900">{abRes.count}</p>
                            <p className="text-xs text-gray-400 uppercase tracking-wider">Total Tests</p>
                        </div>
                    </div>
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                    <div className="flex items-center gap-3">
                        <div className="bg-amber-100 p-2.5 rounded-lg"><Eye className="text-amber-600" size={20} /></div>
                        <div>
                            <p className="text-2xl font-black text-gray-900">{abRes.active_count}</p>
                            <p className="text-xs text-gray-400 uppercase tracking-wider">Active</p>
                        </div>
                    </div>
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                    <div className="flex items-center gap-3">
                        <div className="bg-purple-100 p-2.5 rounded-lg"><Trophy className="text-purple-600" size={20} /></div>
                        <div>
                            <p className="text-2xl font-black text-gray-900">{abRes.winners_count}</p>
                            <p className="text-xs text-gray-400 uppercase tracking-wider">Winners Picked</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Per-test variant tables */}
            {paginatedAbTests.map(test => (
                <div key={test.article_id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <FlaskConical size={18} className={test.is_active ? 'text-emerald-500' : 'text-gray-400'} />
                            <h3 className="text-sm font-bold text-gray-900 truncate max-w-[500px]">{test.article_title}</h3>
                        </div>
                        <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${test.is_active
                            ? 'bg-emerald-100 text-emerald-700'
                            : 'bg-gray-100 text-gray-500'
                            }`}>
                            {test.is_active ? 'Active' : 'Completed'}
                        </span>
                    </div>
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-gray-100">
                                <th className="pb-2 text-left text-gray-400 font-medium">Variant</th>
                                <th className="pb-2 text-left text-gray-400 font-medium">Title</th>
                                <th className="pb-2 text-right text-gray-400 font-medium">Impressions</th>
                                <th className="pb-2 text-right text-gray-400 font-medium">Clicks</th>
                                <th className="pb-2 text-right text-gray-400 font-medium">CTR</th>
                                <th className="pb-2 text-right text-gray-400 font-medium">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {test.variants.map(v => (
                                <tr key={v.id} className={v.is_winner ? 'bg-emerald-50/50' : ''}>
                                    <td className="py-2.5 font-mono text-xs text-gray-500">{v.variant}</td>
                                    <td className="py-2.5 text-gray-800 truncate max-w-[300px]">{v.title}</td>
                                    <td className="py-2.5 text-right font-semibold text-gray-700">{v.impressions.toLocaleString()}</td>
                                    <td className="py-2.5 text-right font-semibold text-gray-700">
                                        <span className="inline-flex items-center gap-1">
                                            <MousePointerClick size={12} className="text-gray-400" />
                                            {v.clicks.toLocaleString()}
                                        </span>
                                    </td>
                                    <td className="py-2.5 text-right">
                                        <span className={`font-bold ${v.ctr >= 5 ? 'text-emerald-600' : v.ctr >= 2 ? 'text-amber-600' : 'text-gray-500'
                                            }`}>
                                            {v.ctr.toFixed(1)}%
                                        </span>
                                    </td>
                                    <td className="py-2.5 text-right">
                                        {v.is_winner && (
                                            <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                                                <Trophy size={12} /> Winner
                                            </span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ))}

            {/* Pagination Controls */}
            {totalAbPages > 1 && (
                <div className="flex items-center justify-between bg-white px-4 py-3 border-t border-gray-200 sm:px-6 rounded-xl shadow-sm">
                    <div className="flex flex-1 justify-between sm:hidden">
                        <button
                            onClick={() => setAbTestPage(p => Math.max(1, p - 1))}
                            disabled={abTestPage === 1}
                            className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none disabled:opacity-50"
                        >
                            Previous
                        </button>
                        <button
                            onClick={() => setAbTestPage(p => Math.min(totalAbPages, p + 1))}
                            disabled={abTestPage === totalAbPages}
                            className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none disabled:opacity-50"
                        >
                            Next
                        </button>
                    </div>
                    <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                        <div>
                            <p className="text-sm text-gray-700">
                                Showing <span className="font-medium">{((abTestPage - 1) * abItemsPerPage) + 1}</span> to <span className="font-medium">{Math.min(abTestPage * abItemsPerPage, abTests.length)}</span> of{' '}
                                <span className="font-medium">{abTests.length}</span> tests
                            </p>
                        </div>
                        <div>
                            <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                                <button
                                    onClick={() => setAbTestPage(p => Math.max(1, p - 1))}
                                    disabled={abTestPage === 1}
                                    className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                                >
                                    <span className="sr-only">Previous</span>
                                    <ArrowDown className="h-4 w-4 rotate-90" aria-hidden="true" />
                                </button>
                                <span className="relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-gray-300 focus:outline-offset-0">
                                    Page {abTestPage} of {totalAbPages}
                                </span>
                                <button
                                    onClick={() => setAbTestPage(p => Math.min(totalAbPages, p + 1))}
                                    disabled={abTestPage === totalAbPages}
                                    className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                                >
                                    <span className="sr-only">Next</span>
                                    <ArrowDown className="h-4 w-4 -rotate-90" aria-hidden="true" />
                                </button>
                            </nav>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
