import React, { ReactNode } from 'react';

interface FormCardProps {
    title: string;
    icon?: ReactNode;
    children: ReactNode;
    className?: string;
    action?: ReactNode;
}

export function FormCard({ title, icon, children, className = '', action }: FormCardProps) {
    return (
        <div className={`bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden ${className}`}>
            <div className="border-b border-gray-100 bg-gray-50/50 p-6 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    {icon && (
                        <div className="p-2 bg-white rounded-lg shadow-sm">
                            {icon}
                        </div>
                    )}
                    <h2 className="text-lg font-semibold text-gray-900">
                        {title}
                    </h2>
                </div>
                {action && <div>{action}</div>}
            </div>
            <div className="p-6">
                {children}
            </div>
        </div>
    );
}

// Helper for standardizing input labels/wrappers inside FormCards
interface FormFieldProps {
    label: string;
    htmlFor?: string;
    required?: boolean;
    description?: string;
    children: ReactNode;
}

export function FormField({ label, htmlFor, required, description, children }: FormFieldProps) {
    return (
        <div className="space-y-2">
            <div className="flex justify-between items-baseline">
                <label htmlFor={htmlFor} className="block text-sm font-medium text-gray-700">
                    {label}
                    {required && <span className="text-red-500 ml-1">*</span>}
                </label>
                {description && (
                    <span className="text-xs text-gray-500">
                        {description}
                    </span>
                )}
            </div>
            {children}
        </div>
    );
}
