'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Gauge, ArrowRight, Zap } from 'lucide-react';

interface SpecsCardLinkProps {
    articleTitle: string;
    tagNames: string[];
}

interface BrandInfo {
    name: string;
    slug: string;
}

interface ModelInfo {
    model: string;
    slug: string;
}

interface BrandDetail {
    brand: string;
    slug: string;
    models: ModelInfo[];
}

export default function SpecsCardLink({ articleTitle, tagNames }: SpecsCardLinkProps) {
    const [carsLink, setCarsLink] = useState<string | null>(null);
    const [brandName, setBrandName] = useState('');
    const [modelName, setModelName] = useState('');

    useEffect(() => {
        const findCarsPage = async () => {
            try {
                const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

                // Step 1: Get known brands
                const brandsRes = await fetch(`${API_BASE}/cars/brands/`);
                if (!brandsRes.ok) return;
                const brands: BrandInfo[] = await brandsRes.json();
                const brandMap = new Map(brands.map(b => [b.name.toLowerCase(), b]));

                // Step 2: Find matching brand in article tags
                let matchedBrand: BrandInfo | null = null;
                for (const tag of tagNames) {
                    const brand = brandMap.get(tag.toLowerCase());
                    if (brand) {
                        matchedBrand = brand;
                        break;
                    }
                }
                if (!matchedBrand) return;

                // Step 3: Get brand's models
                const brandRes = await fetch(`${API_BASE}/cars/brands/${matchedBrand.slug}/`);
                if (!brandRes.ok) return;
                const brandDetail: BrandDetail = await brandRes.json();

                if (!brandDetail.models || brandDetail.models.length === 0) return;

                // Step 4: Match model from article title
                // Title: "2026 BYD Qin L DM-i Review" — find "Qin L" in model list
                const titleLower = articleTitle.toLowerCase();
                let bestMatch: ModelInfo | null = null;
                let bestMatchLen = 0;

                for (const model of brandDetail.models) {
                    const modelLower = model.model.toLowerCase();
                    if (titleLower.includes(modelLower) && modelLower.length > bestMatchLen) {
                        bestMatch = model;
                        bestMatchLen = modelLower.length;
                    }
                }

                if (!bestMatch) return;

                setCarsLink(`/cars/${matchedBrand.slug}/${bestMatch.slug}`);
                setBrandName(matchedBrand.name);
                setModelName(bestMatch.model);
            } catch {
                // Silently fail
            }
        };

        if (tagNames.length > 0) {
            findCarsPage();
        }
    }, [articleTitle, tagNames]);

    if (!carsLink) return null;

    return (
        <div className="relative overflow-hidden rounded-xl shadow-lg">
            {/* Gradient background */}
            <div className="absolute inset-0 bg-gradient-to-r from-indigo-600 via-blue-600 to-cyan-500" />

            {/* Decorative circles */}
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute -top-12 -right-12 w-48 h-48 bg-white/10 rounded-full" />
                <div className="absolute -bottom-8 -left-8 w-36 h-36 bg-white/10 rounded-full" />
            </div>

            <Link
                href={carsLink}
                className="relative flex items-center justify-between p-5 sm:p-6 group"
            >
                <div className="flex items-center gap-4">
                    {/* Icon */}
                    <div className="flex-shrink-0 w-12 h-12 sm:w-14 sm:h-14 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center group-hover:bg-white/30 transition-all duration-300 group-hover:scale-110">
                        <Gauge className="w-6 h-6 sm:w-7 sm:h-7 text-white" />
                    </div>

                    {/* Text */}
                    <div>
                        <div className="text-white/90 text-xs sm:text-sm font-semibold uppercase tracking-wider mb-0.5">
                            Full Specifications
                        </div>
                        <div className="text-white text-lg sm:text-xl font-bold leading-tight">
                            {brandName} {modelName}
                        </div>
                        <div className="text-white/80 text-xs sm:text-sm mt-1 flex items-center gap-2 font-medium">
                            <span className="flex items-center gap-1">
                                <Zap className="w-3.5 h-3.5" />
                                Performance
                            </span>
                            <span className="text-white/50">•</span>
                            <span>Dimensions</span>
                            <span className="text-white/50">•</span>
                            <span>Pricing</span>
                        </div>
                    </div>
                </div>

                {/* Arrow */}
                <div className="flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center group-hover:bg-white/30 group-hover:translate-x-1 transition-all duration-300">
                    <ArrowRight className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
                </div>
            </Link>
        </div>
    );
}
