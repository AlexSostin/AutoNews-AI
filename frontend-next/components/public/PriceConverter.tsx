'use client';

import { useState, useEffect } from 'react';
import { DollarSign, Euro, ChevronDown } from 'lucide-react';

interface CurrencyRates {
  USD: number;
  EUR: number;
  CNY: number;
  GBP: number;
  JPY: number;
  updated_at: string;
}

interface PriceConverterProps {
  priceUsd: number | null;
  className?: string;
}

const currencies = [
  { code: 'USD', symbol: '$', name: 'US Dollar', icon: DollarSign },
  { code: 'EUR', symbol: '€', name: 'Euro', icon: Euro },
  { code: 'CNY', symbol: '¥', name: 'Chinese Yuan', icon: null },
  { code: 'GBP', symbol: '£', name: 'British Pound', icon: null },
  { code: 'JPY', symbol: '¥', name: 'Japanese Yen', icon: null },
];

export default function PriceConverter({ priceUsd, className = '' }: PriceConverterProps) {
  const [rates, setRates] = useState<CurrencyRates | null>(null);
  const [selectedCurrency, setSelectedCurrency] = useState('USD');
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRates = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';
        const response = await fetch(`${apiUrl}/currency-rates/`);
        if (response.ok) {
          const data = await response.json();
          setRates(data);
        }
      } catch (error) {
        console.error('Failed to fetch currency rates:', error);
        // Use fallback rates
        setRates({
          USD: 1,
          EUR: 0.92,
          CNY: 7.25,
          GBP: 0.79,
          JPY: 148.5,
          updated_at: 'fallback'
        });
      } finally {
        setLoading(false);
      }
    };

    fetchRates();
  }, []);

  if (!priceUsd || priceUsd <= 0) {
    return null;
  }

  const convertedPrice = rates 
    ? priceUsd * (rates[selectedCurrency as keyof CurrencyRates] as number || 1)
    : priceUsd;
  
  const formatPrice = (price: number, currencyCode: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currencyCode,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(price);
  };

  return (
    <div className={`relative inline-flex items-center gap-2 ${className}`}>
      {/* Price Display */}
      <div className="flex items-center gap-1 bg-gradient-to-r from-green-500 to-emerald-600 text-white px-4 py-2 rounded-lg font-bold text-lg shadow-md">
        {loading ? (
          <span className="animate-pulse">...</span>
        ) : (
          <span>{formatPrice(convertedPrice, selectedCurrency)}</span>
        )}
      </div>

      {/* Currency Selector */}
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-1 bg-gray-100 hover:bg-gray-200 px-3 py-2 rounded-lg transition-colors text-sm font-medium"
        >
          <span>{selectedCurrency}</span>
          <ChevronDown size={16} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {/* Dropdown */}
        {isOpen && (
          <div className="absolute top-full right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-xl z-50 min-w-[160px] overflow-hidden">
            {currencies.map((currency) => {
              const convertedForPreview = rates 
                ? priceUsd * (rates[currency.code as keyof CurrencyRates] as number || 1)
                : priceUsd;
              
              return (
                <button
                  key={currency.code}
                  onClick={() => {
                    setSelectedCurrency(currency.code);
                    setIsOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-50 transition-colors ${
                    selectedCurrency === currency.code ? 'bg-purple-50 text-purple-700' : ''
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <span className="font-medium">{currency.symbol}</span>
                    <span className="text-gray-600">{currency.code}</span>
                  </span>
                  <span className="text-gray-500 text-xs">
                    {formatPrice(convertedForPreview, currency.code)}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Click outside to close */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}
