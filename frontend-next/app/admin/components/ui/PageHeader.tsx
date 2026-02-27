import React from 'react';
import Link from 'next/link';
import { ArrowLeft, Save, Trash2, Loader2, RefreshCw } from 'lucide-react';

interface PageHeaderProps {
    title: string;
    backHref?: string;
    onSave?: () => void;
    onDelete?: () => void;
    onRefresh?: () => void;
    isSaving?: boolean;
    isDeleting?: boolean;
    isRefreshing?: boolean;
    saveText?: string;
}

export function PageHeader({
    title,
    backHref,
    onSave,
    onDelete,
    onRefresh,
    isSaving = false,
    isDeleting = false,
    isRefreshing = false,
    saveText = 'Save Changes'
}: PageHeaderProps) {
    return (
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8 bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
            <div className="flex items-center gap-4">
                {backHref && (
                    <Link
                        href={backHref}
                        className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-500"
                    >
                        <ArrowLeft size={20} />
                    </Link>
                )}
                <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600">
                    {title}
                </h1>
            </div>

            <div className="flex gap-3 w-full sm:w-auto">
                {onRefresh && (
                    <button
                        onClick={onRefresh}
                        disabled={isRefreshing}
                        className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all disabled:opacity-50"
                    >
                        {isRefreshing ? <Loader2 size={18} className="animate-spin" /> : <RefreshCw size={18} />}
                        <span className="hidden sm:inline">Refresh</span>
                    </button>
                )}

                {onDelete && (
                    <button
                        onClick={onDelete}
                        disabled={isDeleting || isSaving}
                        className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 text-red-600 bg-red-50 hover:bg-red-100 rounded-xl transition-all disabled:opacity-50"
                    >
                        {isDeleting ? <Loader2 size={18} className="animate-spin" /> : <Trash2 size={18} />}
                        <span className="hidden sm:inline">Delete</span>
                    </button>
                )}

                {onSave && (
                    <button
                        onClick={onSave}
                        disabled={isSaving || isDeleting}
                        className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-xl font-medium transition-all shadow-md shadow-indigo-500/20 disabled:opacity-50 disabled:shadow-none"
                    >
                        {isSaving ? (
                            <Loader2 size={18} className="animate-spin" />
                        ) : (
                            <Save size={18} />
                        )}
                        {saveText}
                    </button>
                )}
            </div>
        </div>
    );
}
