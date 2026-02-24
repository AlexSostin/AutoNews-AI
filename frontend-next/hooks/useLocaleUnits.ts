'use client';

import { useState, useEffect, useCallback } from 'react';

// ─── Types ───────────────────────────────────────────────────────────
export type UnitSystem = 'metric' | 'imperial';
export type CurrencyCode = 'USD' | 'EUR' | 'GBP' | 'CNY' | 'JPY';

export interface LocaleUnits {
    system: UnitSystem;
    currency: CurrencyCode;
    setSystem: (system: UnitSystem) => void;
    setCurrency: (currency: CurrencyCode) => void;
    formatDistance: (km: number | null) => string;
    formatSpeed: (kmh: number | null) => string;
    formatAcceleration: (seconds: number | null, label?: boolean) => string;
    distanceUnit: string;   // 'km' or 'mi'
    speedUnit: string;      // 'km/h' or 'mph'
    ready: boolean;
}

// ─── Conversion ──────────────────────────────────────────────────────
const KM_TO_MILES = 0.621371;

export function kmToMiles(km: number): number {
    return Math.round(km * KM_TO_MILES);
}

export function kmhToMph(kmh: number): number {
    return Math.round(kmh * KM_TO_MILES);
}

// ─── Country Detection ───────────────────────────────────────────────

// Timezones that map to imperial countries
const IMPERIAL_TIMEZONES = new Set([
    // United States
    'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
    'America/Anchorage', 'America/Adak', 'America/Phoenix', 'America/Boise',
    'America/Indiana/Indianapolis', 'America/Indiana/Knox', 'America/Indiana/Marengo',
    'America/Indiana/Petersburg', 'America/Indiana/Tell_City', 'America/Indiana/Vevay',
    'America/Indiana/Vincennes', 'America/Indiana/Winamac', 'America/Kentucky/Louisville',
    'America/Kentucky/Monticello', 'America/Menominee', 'America/Nome',
    'America/North_Dakota/Beulah', 'America/North_Dakota/Center',
    'America/North_Dakota/New_Salem', 'America/Sitka', 'America/Yakutat',
    'America/Detroit', 'America/Juneau', 'Pacific/Honolulu',
    // UK
    'Europe/London',
]);

// UK-specific timezones (for GBP currency)
const UK_TIMEZONES = new Set(['Europe/London']);

// Map language codes to currency
const LANGUAGE_TO_CURRENCY: Record<string, CurrencyCode> = {
    'en-US': 'USD',
    'en-GB': 'GBP',
    'en-AU': 'USD', // AUD not in our list, fallback to USD
    'de': 'EUR', 'de-DE': 'EUR', 'de-AT': 'EUR', 'de-CH': 'EUR',
    'fr': 'EUR', 'fr-FR': 'EUR', 'fr-BE': 'EUR', 'fr-CH': 'EUR',
    'es': 'EUR', 'es-ES': 'EUR',
    'it': 'EUR', 'it-IT': 'EUR',
    'nl': 'EUR', 'nl-NL': 'EUR', 'nl-BE': 'EUR',
    'pt': 'EUR', 'pt-PT': 'EUR',
    'ja': 'JPY', 'ja-JP': 'JPY',
    'zh': 'CNY', 'zh-CN': 'CNY', 'zh-TW': 'CNY',
};

// Map timezone to currency
const TIMEZONE_TO_CURRENCY: Record<string, CurrencyCode> = {
    'Europe/London': 'GBP',
    'Asia/Tokyo': 'JPY',
    'Asia/Shanghai': 'CNY', 'Asia/Chongqing': 'CNY', 'Asia/Harbin': 'CNY',
    'Asia/Urumqi': 'CNY', 'Asia/Kashgar': 'CNY',
};

function detectCountry(): { system: UnitSystem; currency: CurrencyCode } {
    if (typeof window === 'undefined') {
        return { system: 'metric', currency: 'USD' };
    }

    // Step 1: Get timezone
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    // Step 2: Get language
    const lang = navigator.language || 'en-US';

    // Step 3: Determine unit system
    // Timezone is more reliable than language for unit system
    const isImperial = IMPERIAL_TIMEZONES.has(timezone);

    // Step 4: Determine currency
    // Priority: timezone-specific > language-specific > USD fallback
    let currency: CurrencyCode = 'USD';

    if (TIMEZONE_TO_CURRENCY[timezone]) {
        currency = TIMEZONE_TO_CURRENCY[timezone];
    } else if (isImperial && !UK_TIMEZONES.has(timezone)) {
        currency = 'USD'; // US timezone = USD
    } else if (isImperial && UK_TIMEZONES.has(timezone)) {
        currency = 'GBP'; // UK timezone = GBP
    } else {
        // Check language
        if (LANGUAGE_TO_CURRENCY[lang]) {
            currency = LANGUAGE_TO_CURRENCY[lang];
        } else {
            // Try base language (e.g., 'de' from 'de-DE')
            const baseLang = lang.split('-')[0];
            if (LANGUAGE_TO_CURRENCY[baseLang]) {
                currency = LANGUAGE_TO_CURRENCY[baseLang];
            }
        }

        // European timezone heuristic
        if (currency === 'USD' && timezone.startsWith('Europe/') && !UK_TIMEZONES.has(timezone)) {
            currency = 'EUR';
        }
    }

    return { system: isImperial ? 'imperial' : 'metric', currency };
}

// ─── Storage Keys ────────────────────────────────────────────────────
const STORAGE_KEY_SYSTEM = 'freshmotors_unit_system';
const STORAGE_KEY_CURRENCY = 'freshmotors_currency';

// ─── Hook ────────────────────────────────────────────────────────────
export function useLocaleUnits(): LocaleUnits {
    const [system, setSystemState] = useState<UnitSystem>('metric');
    const [currency, setCurrencyState] = useState<CurrencyCode>('USD');
    const [ready, setReady] = useState(false);

    useEffect(() => {
        // Check localStorage first (manual override)
        const savedSystem = localStorage.getItem(STORAGE_KEY_SYSTEM) as UnitSystem | null;
        const savedCurrency = localStorage.getItem(STORAGE_KEY_CURRENCY) as CurrencyCode | null;

        if (savedSystem && savedCurrency) {
            setSystemState(savedSystem);
            setCurrencyState(savedCurrency);
        } else {
            // Auto-detect
            const detected = detectCountry();
            setSystemState(savedSystem || detected.system);
            setCurrencyState(savedCurrency || detected.currency);

            // Save detected values
            if (!savedSystem) localStorage.setItem(STORAGE_KEY_SYSTEM, detected.system);
            if (!savedCurrency) localStorage.setItem(STORAGE_KEY_CURRENCY, detected.currency);
        }
        setReady(true);

        // Listen for changes from other components or tabs
        const handleStorageChange = () => {
            const newSystem = localStorage.getItem(STORAGE_KEY_SYSTEM) as UnitSystem | null;
            const newCurrency = localStorage.getItem(STORAGE_KEY_CURRENCY) as CurrencyCode | null;
            if (newSystem) setSystemState(newSystem);
            if (newCurrency) setCurrencyState(newCurrency);
        };

        window.addEventListener('localeUnitsChanged', handleStorageChange);
        window.addEventListener('storage', handleStorageChange);

        return () => {
            window.removeEventListener('localeUnitsChanged', handleStorageChange);
            window.removeEventListener('storage', handleStorageChange);
        };
    }, []);

    const setSystem = useCallback((s: UnitSystem) => {
        setSystemState(s);
        localStorage.setItem(STORAGE_KEY_SYSTEM, s);
        window.dispatchEvent(new Event('localeUnitsChanged'));
    }, []);

    const setCurrency = useCallback((c: CurrencyCode) => {
        setCurrencyState(c);
        localStorage.setItem(STORAGE_KEY_CURRENCY, c);
        window.dispatchEvent(new Event('localeUnitsChanged'));
    }, []);

    const formatDistance = useCallback((km: number | null): string => {
        if (km === null || km === undefined) return '';
        if (system === 'imperial') {
            return `${kmToMiles(km).toLocaleString()} mi`;
        }
        return `${km.toLocaleString()} km`;
    }, [system]);

    const formatSpeed = useCallback((kmh: number | null): string => {
        if (kmh === null || kmh === undefined) return '';
        if (system === 'imperial') {
            return `${kmhToMph(kmh)} mph`;
        }
        return `${kmh} km/h`;
    }, [system]);

    const formatAcceleration = useCallback((seconds: number | null, label: boolean = true): string => {
        if (seconds === null || seconds === undefined) return '';
        if (system === 'imperial') {
            // 0-60 mph ≈ 0-96.6 km/h, roughly 0-100 * 0.966
            // But the actual difference is negligible for display
            return label ? `${seconds}s (0-60 mph)` : `${seconds}s`;
        }
        return label ? `${seconds}s (0-100 km/h)` : `${seconds}s`;
    }, [system]);

    return {
        system,
        currency,
        setSystem,
        setCurrency,
        formatDistance,
        formatSpeed,
        formatAcceleration,
        distanceUnit: system === 'imperial' ? 'mi' : 'km',
        speedUnit: system === 'imperial' ? 'mph' : 'km/h',
        ready,
    };
}
