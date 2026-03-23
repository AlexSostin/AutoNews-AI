'use client';

import { useState, useEffect, useCallback } from 'react';
import { authenticatedFetch } from '@/lib/authenticatedFetch';
import toast from 'react-hot-toast';
import {
    BrainCircuit, Loader2, ThumbsUp, ThumbsDown, ArrowRight,
    CarFront, Trophy, AlertCircle, RefreshCw, Hand, Target, CheckCircle2, MessageSquare
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface CarSpec {
    make: string;
    model: string;
    trim: string;
    photo: string;
    price_usd: number | null;
    power_hp: number | null;
    range_km: number | null;
    body_type: string | null;
    fuel_type: string | null;
    article_id: number | null;
}

interface Stats {
    daily_count: number;
    total_count: number;
}

export default function MLTrainingPage() {
    const [stats, setStats] = useState<Stats>({ daily_count: 0, total_count: 0 });
    const [subject, setSubject] = useState<CarSpec | null>(null);
    const [competitor, setCompetitor] = useState<CarSpec | null>(null);
    
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    
    // Inline Form State
    const [selectedScore, setSelectedScore] = useState<number | null>(null);
    const [selectedReasons, setSelectedReasons] = useState<string[]>([]);
    const [customNote, setCustomNote] = useState('');

    const FEEDBACK_CATEGORIES = [
        {
            title: 'Price Comparison',
            options: [
                { id: 'price_similar', label: 'Similar Price (±10%)' },
                { id: 'comp_cheaper', label: 'Suggestion is cheaper' },
                { id: 'comp_expensive', label: 'Suggestion is more expensive' },
            ]
        },
        {
            title: 'Body / Size',
            options: [
                { id: 'body_same', label: 'Same Body Type & Segment' },
                { id: 'comp_larger', label: 'Suggestion is visibly larger/higher segment' },
                { id: 'comp_smaller', label: 'Suggestion is smaller' },
                { id: 'body_mismatch', label: 'Completely different format (e.g. SUV vs Sedan)' },
            ]
        },
        {
            title: 'Performance & Tech',
            options: [
                { id: 'specs_similar', label: 'Similar Specs & Range' },
                { id: 'comp_faster', label: 'Suggestion is notably more powerful' },
                { id: 'comp_better_range', label: 'Suggestion has better range/battery' },
                { id: 'fuel_mismatch', label: 'Fuel mismatch (e.g. EV vs ICE)' },
            ]
        },
        {
            title: 'Brand Tier / Prestige',
            options: [
                { id: 'tier_same', label: 'Same Brand Tier' },
                { id: 'comp_premium', label: 'Suggestion is more Premium/Luxury' },
                { id: 'comp_budget', label: 'Suggestion is more Budget/Mass-market' },
            ]
        }
    ];

    const fetchNextPair = useCallback(async () => {
        setLoading(true);
        setSelectedScore(null);
        setSelectedReasons([]);
        setCustomNote('');
        try {
            const res = await authenticatedFetch(`${API_BASE}/admin/ml-training/next-pair/`);
            if (!res.ok) {
                if (res.status === 404) {
                    toast.error('No candidate pairs found right now.');
                } else {
                    throw new Error('Failed to fetch next pair');
                }
                return;
            }
            const data = await res.json();
            setStats(data.stats);
            setSubject(data.subject);
            setCompetitor(data.competitor);
        } catch (err) {
            console.error('Failed to fetch ML pair:', err);
            toast.error('Failed to load candidate pair');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchNextPair();
    }, [fetchNextPair]);

    const submitFeedback = async () => {
        if (!subject || !competitor || selectedScore === null) return;
        
        // Combine reasons and custom note
        let finalReason = selectedReasons.join(', ');
        if (customNote.trim()) {
            finalReason += finalReason ? ` | Note: ${customNote.trim()}` : `Note: ${customNote.trim()}`;
        }
        
        setSubmitting(true);
        try {
            const res = await authenticatedFetch(`${API_BASE}/admin/ml-training/submit-feedback/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    subject_make: subject.make,
                    subject_model: subject.model,
                    competitor_make: competitor.make,
                    competitor_model: competitor.model,
                    score: selectedScore,
                    penalty_reason: finalReason
                }),
            });
            
            if (res.ok) {
                toast.success('Feedback submitted!');
                fetchNextPair(); // Loads next immediately
            } else {
                const errData = await res.json();
                toast.error(errData.detail || 'Failed to submit feedback');
                setSubmitting(false);
            }
        } catch (err) {
            console.error(err);
            toast.error('Network error while submitting feedback');
            setSubmitting(false);
        }
    };

    const handleScoreClick = (score: number) => {
        setSelectedScore(score);
        // We do *not* clear selectedReasons or customNote here 
        // in case they are just switching tabs/scores.
    };

    const toggleReason = (reasonId: string) => {
        setSelectedReasons(prev => 
            prev.includes(reasonId) ? prev.filter(r => r !== reasonId) : [...prev, reasonId]
        );
    };

    const CarCard = ({ car, isSubject }: { car: CarSpec, isSubject: boolean }) => (
        <div className={`p-6 rounded-2xl border-2 flex flex-col h-full bg-white shadow-sm transition-all ${isSubject ? 'border-indigo-200 ring-2 ring-indigo-50' : 'border-gray-200'}`}>
            <div className="flex items-center justify-between mb-4">
                <span className={`px-3 py-1 rounded-full text-xs font-bold tracking-wider uppercase ${isSubject ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600'}`}>
                    {isSubject ? 'Subject Car' : 'AI Suggestion'}
                </span>
            </div>
            
            <div className="aspect-video bg-gray-100 rounded-xl overflow-hidden mb-5 relative border border-gray-100 flex items-center justify-center">
                {car.photo ? (
                    <img src={car.photo} alt={`${car.make} ${car.model}`} className="w-full h-full object-cover" />
                ) : (
                    <CarFront className="w-16 h-16 text-gray-300" />
                )}
            </div>
            
            <h2 className="text-2xl font-bold text-gray-900 leading-tight mb-1">{car.make} {car.model}</h2>
            <p className="text-gray-500 text-sm mb-5 min-h-[40px]">{car.trim}</p>
            
            <div className="space-y-3 mt-auto border-t border-gray-100 pt-5">
                <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-500 font-medium">Est. Price</span>
                    <span className="font-semibold text-gray-900">{car.price_usd ? `$${car.price_usd.toLocaleString()}` : 'N/A'}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-500 font-medium">Body Type</span>
                    <span className="font-semibold text-gray-900 capitalize">{car.body_type || 'Unknown'}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-500 font-medium">Fuel Type</span>
                    <span className="font-semibold text-gray-900 capitalize">{car.fuel_type || 'Unknown'}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-500 font-medium">Power</span>
                    <span className="font-semibold text-gray-900">{car.power_hp ? `${car.power_hp} HP` : 'N/A'}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-500 font-medium">Range</span>
                    <span className="font-semibold text-gray-900">{car.range_km ? `${car.range_km} km` : 'N/A'}</span>
                </div>
            </div>
            
            {car.article_id && (
                <div className="mt-4 pt-4 border-t border-gray-100 flex justify-center">
                    <a 
                        href={`/admin/articles/${car.article_id}`} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-xs text-indigo-600 hover:text-indigo-800 font-medium underline underline-offset-2 flex items-center transition-colors"
                        title="Edit this article in a new tab"
                    >
                        Edit Article Data to Fix Specs
                    </a>
                </div>
            )}
        </div>
    );

    if (loading && !subject) {
        return (
            <div className="flex flex-col items-center justify-center h-[70vh]">
                <Loader2 className="w-12 h-12 text-indigo-600 animate-spin mb-4" />
                <h2 className="text-xl font-medium text-gray-900">Finding the perfect pair to match...</h2>
                <p className="text-gray-500 mt-2">Warming up the AI comparison engine</p>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto pb-20">
            {/* Header / Gamification Bar */}
            <div className="flex items-center justify-between mb-8 bg-white p-5 rounded-2xl border border-gray-200 shadow-sm">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-inner">
                        <BrainCircuit className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-xl font-extrabold text-gray-900">ML Competitor Trainer</h1>
                        <p className="text-gray-500 text-sm">Help the AI learn which cars actually compete</p>
                    </div>
                </div>
                
                <div className="flex items-center gap-6">
                    <div className="text-right">
                        <p className="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">Pairs Labeled Today</p>
                        <div className="flex items-center justify-end gap-2">
                            <Trophy className="w-5 h-5 text-amber-500" />
                            <span className="text-2xl font-black text-gray-900 leading-none">{stats.daily_count}</span>
                        </div>
                    </div>
                    <div className="h-10 w-px bg-gray-200"></div>
                    <div className="text-right">
                        <p className="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">Total Contribution</p>
                        <div className="flex items-center justify-end gap-2">
                            <Target className="w-4 h-4 text-emerald-500" />
                            <span className="text-xl font-bold text-gray-700 leading-none">{stats.total_count}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Stage */}
            {subject && competitor ? (
                <div className="relative">
                    {/* The VS Badge */}
                    <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 hidden md:flex flex-col items-center justify-center">
                        <div className="w-16 h-16 bg-white border-4 border-gray-100 rounded-full flex items-center justify-center shadow-lg transform -translate-y-12">
                            <span className="text-xl font-black italic text-gray-400">VS</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
                        <CarCard car={subject} isSubject={true} />
                        <CarCard car={competitor} isSubject={false} />
                    </div>

                    {/* Action Panel */}
                    <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-xl shadow-gray-100/50">
                        {selectedScore === null ? (
                            <>
                                <div className="text-center mb-6 animate-in fade-in slide-in-from-bottom-2">
                                    <h3 className="text-lg font-bold text-gray-900">Are these cars direct competitors?</h3>
                                    <p className="text-gray-500 text-sm mt-1">Select the best description for this pairing.</p>
                                </div>
                                <div className="flex flex-col sm:flex-row gap-4 justify-center animate-in fade-in slide-in-from-bottom-2">
                                    <button
                                        disabled={submitting}
                                        onClick={() => handleScoreClick(1.0)}
                                        className="flex-1 max-w-xs flex flex-col items-center justify-center gap-2 p-4 rounded-xl border-2 border-emerald-100 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 hover:border-emerald-300 transition-all focus:ring-4 focus:ring-emerald-50 disabled:opacity-50"
                                    >
                                        <ThumbsUp className="w-8 h-8 mb-1" />
                                        <span className="font-bold">Perfect Match</span>
                                        <span className="text-xs opacity-80 font-medium">Score: 1.0</span>
                                    </button>
                                    
                                    <button
                                        disabled={submitting}
                                        onClick={() => handleScoreClick(0.5)}
                                        className="flex-1 max-w-xs flex flex-col items-center justify-center gap-2 p-4 rounded-xl border-2 border-amber-100 bg-amber-50 text-amber-700 hover:bg-amber-100 hover:border-amber-300 transition-all focus:ring-4 focus:ring-amber-50 disabled:opacity-50"
                                    >
                                        <Hand className="w-8 h-8 mb-1" />
                                        <span className="font-bold">Acceptable Match</span>
                                        <span className="text-xs opacity-80 font-medium">Score: 0.5</span>
                                    </button>
                                    
                                    <button
                                        disabled={submitting}
                                        onClick={() => handleScoreClick(-1.0)}
                                        className="flex-1 max-w-xs flex flex-col items-center justify-center gap-2 p-4 rounded-xl border-2 border-rose-100 bg-rose-50 text-rose-700 hover:bg-rose-100 hover:border-rose-300 transition-all focus:ring-4 focus:ring-rose-50 disabled:opacity-50"
                                    >
                                        <ThumbsDown className="w-8 h-8 mb-1" />
                                        <span className="font-bold">Bad Match</span>
                                        <span className="text-xs opacity-80 font-medium">Score: -1.0</span>
                                    </button>
                                </div>
                            </>
                        ) : (
                            <div className="animate-in fade-in slide-in-from-top-2">
                                <div className={`p-4 mb-6 rounded-xl border flex items-center justify-between ${
                                    selectedScore === 1.0 ? 'bg-emerald-50 border-emerald-200 text-emerald-900' :
                                    selectedScore === 0.5 ? 'bg-amber-50 border-amber-200 text-amber-900' :
                                    'bg-rose-50 border-rose-200 text-rose-900'
                                }`}>
                                    <div className="flex items-center gap-3">
                                        {selectedScore === 1.0 && <><ThumbsUp className="w-6 h-6 text-emerald-600" /><h3 className="text-xl font-bold">What makes this a Perfect Match?</h3></>}
                                        {selectedScore === 0.5 && <><Hand className="w-6 h-6 text-amber-600" /><h3 className="text-xl font-bold">What differs in this Acceptable Match?</h3></>}
                                        {selectedScore === -1.0 && <><ThumbsDown className="w-6 h-6 text-rose-600" /><h3 className="text-xl font-bold">Why is this a Bad Match?</h3></>}
                                    </div>
                                    <button 
                                        onClick={() => setSelectedScore(null)} 
                                        className="text-sm border border-current px-3 py-1.5 rounded-lg opacity-70 hover:opacity-100 flex items-center gap-2 transition-opacity"
                                    >
                                        Change Score
                                    </button>
                                </div>

                                <p className="text-gray-600 mb-4 text-sm font-medium">Select all that apply to help the AI learn the specific features of this pairing (relative to Subject Car).</p>
                                
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                                    {FEEDBACK_CATEGORIES.map((category) => (
                                        <div key={category.title} className="space-y-2 bg-gray-50 p-4 rounded-xl border border-gray-100">
                                            <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">{category.title}</h4>
                                            <div className="space-y-2">
                                                {category.options.map(opt => {
                                                    const isSelected = selectedReasons.includes(opt.id);
                                                    return (
                                                        <button
                                                            key={opt.id}
                                                            onClick={() => toggleReason(opt.id)}
                                                            className={`w-full flex items-start gap-2 text-left p-2.5 rounded-lg border text-sm transition-colors focus:outline-none ${
                                                                isSelected 
                                                                    ? 'bg-indigo-50 border-indigo-200 text-indigo-800 font-medium ring-1 ring-indigo-200 shadow-sm' 
                                                                    : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50 shadow-sm'
                                                            }`}
                                                        >
                                                            <div className="mt-0.5 flex-shrink-0">
                                                                <div className={`w-4 h-4 rounded-sm border flex items-center justify-center ${isSelected ? 'bg-indigo-600 border-indigo-600' : 'border-gray-300'}`}>
                                                                    {isSelected && <CheckCircle2 className="w-3 h-3 text-white" strokeWidth={3} />}
                                                                </div>
                                                            </div>
                                                            <span className="leading-tight">{opt.label}</span>
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                <div className="mb-6">
                                    <label className="flex items-center gap-2 text-sm font-bold text-gray-700 mb-2">
                                        <MessageSquare className="w-4 h-4 text-gray-400" /> Additional Notes (Optional)
                                    </label>
                                    <textarea
                                        value={customNote}
                                        onChange={(e) => setCustomNote(e.target.value)}
                                        placeholder="Write any custom observations here..."
                                        className="w-full border border-gray-200 rounded-xl p-3 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none min-h-[80px]"
                                    />
                                </div>

                                <div className="flex justify-end pt-5 border-t border-gray-100">
                                    <button
                                        onClick={submitFeedback}
                                        disabled={submitting}
                                        className="px-8 py-3 bg-indigo-600 text-white rounded-xl font-bold text-sm shadow-md shadow-indigo-200 hover:bg-indigo-700 focus:ring-4 focus:ring-indigo-100 transition-all disabled:opacity-50 flex items-center gap-2"
                                    >
                                        {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                                        Submit Feedback & Next
                                    </button>
                                </div>
                            </div>
                        )}

                        <div className="mt-8 flex justify-center">
                            <button
                                disabled={submitting || loading}
                                onClick={() => fetchNextPair()}
                                className="text-sm text-gray-400 hover:text-gray-600 flex items-center gap-2 transition-colors disabled:opacity-50"
                            >
                                <RefreshCw className={`w-4 h-4 ${submitting ? 'animate-spin' : ''}`} />
                                Skip to next pair
                            </button>
                        </div>
                    </div>
                </div>
            ) : null}

        </div>
    );
}
