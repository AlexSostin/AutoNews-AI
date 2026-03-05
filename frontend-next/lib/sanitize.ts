import DOMPurify from 'dompurify';

/**
 * Sanitize HTML content to prevent XSS attacks.
 * Strips <script>, event handlers (onclick, onerror), and other dangerous elements.
 * Safe for use with dangerouslySetInnerHTML.
 *
 * On the server (SSR), returns html as-is since DOMPurify requires a DOM.
 * The client-side render will sanitize it.
 */
export function sanitizeHtml(html: string): string {
    if (typeof window === 'undefined') return html;
    return DOMPurify.sanitize(html, {
        ALLOWED_TAGS: [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'a', 'ul', 'ol', 'li',
            'strong', 'em', 'b', 'i', 'u', 'br', 'hr',
            'img', 'div', 'span',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'blockquote', 'figure', 'figcaption',
            'video', 'source', 'iframe',
            'pre', 'code', 'sup', 'sub', 'mark',
            'dl', 'dt', 'dd', 'abbr', 'details', 'summary',
            'section', 'article', 'header', 'footer', 'nav',
        ],
        ALLOWED_ATTR: [
            'href', 'src', 'alt', 'title', 'class', 'style',
            'width', 'height', 'target', 'rel',
            'loading', 'decoding', 'controls', 'type',
            'frameborder', 'allowfullscreen', 'allow',
            'id', 'name', 'colspan', 'rowspan', 'scope',
            'data-issues', // fact-check block attribute
        ],
        ALLOW_DATA_ATTR: false,
    });
}
