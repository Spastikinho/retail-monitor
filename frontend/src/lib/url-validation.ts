/**
 * URL Validation and Retailer Detection Utility
 * Phase 5 Implementation - Client-side validation with actionable errors
 */

export interface RetailerConfig {
  id: string;
  name: string;
  code: string;
  patterns: RegExp[];
  urlPatterns: RegExp[];
  exampleUrl: string;
}

export const SUPPORTED_RETAILERS: RetailerConfig[] = [
  {
    id: 'ozon',
    name: 'Ozon',
    code: 'ozon',
    patterns: [/ozon\.ru/i],
    urlPatterns: [
      /^https?:\/\/(www\.)?ozon\.ru\/product\/[^\/]+-\d+\/?/i,
      /^https?:\/\/(www\.)?ozon\.ru\/product\/\d+\/?/i,
    ],
    exampleUrl: 'https://www.ozon.ru/product/product-name-123456789/',
  },
  {
    id: 'wildberries',
    name: 'Wildberries',
    code: 'wildberries',
    patterns: [/wildberries\.ru/i, /wb\.ru/i],
    urlPatterns: [
      /^https?:\/\/(www\.)?wildberries\.ru\/catalog\/\d+\/detail\.aspx/i,
      /^https?:\/\/(www\.)?wildberries\.ru\/catalog\/\d+\/?/i,
      /^https?:\/\/(www\.)?wb\.ru\/catalog\/\d+\/?/i,
    ],
    exampleUrl: 'https://www.wildberries.ru/catalog/123456789/detail.aspx',
  },
  {
    id: 'vkusvill',
    name: 'VkusVill',
    code: 'vkusvill',
    patterns: [/vkusvill\.ru/i],
    urlPatterns: [
      /^https?:\/\/(www\.)?vkusvill\.ru\/goods\/[^\/]+-\d+\.html/i,
      /^https?:\/\/(www\.)?vkusvill\.ru\/goods\/\d+\/?/i,
    ],
    exampleUrl: 'https://vkusvill.ru/goods/product-name-12345.html',
  },
  {
    id: 'perekrestok',
    name: 'Perekrestok',
    code: 'perekrestok',
    patterns: [/perekrestok\.ru/i],
    urlPatterns: [
      /^https?:\/\/(www\.)?perekrestok\.ru\/cat\/[^\/]+\/p\/[^\/]+/i,
      /^https?:\/\/(www\.)?perekrestok\.ru\/cat\/\d+\/p\/\d+/i,
    ],
    exampleUrl: 'https://www.perekrestok.ru/cat/123/p/product-456',
  },
  {
    id: 'yandex-lavka',
    name: 'Yandex Lavka',
    code: 'yandex-lavka',
    patterns: [/lavka\.yandex\.ru/i, /eda\.yandex\.ru\/lavka/i],
    urlPatterns: [
      /^https?:\/\/lavka\.yandex\.ru\/[^\/]+\/product\/[^\/]+/i,
      /^https?:\/\/eda\.yandex\.ru\/lavka\/[^\/]+\/product\/[^\/]+/i,
    ],
    exampleUrl: 'https://lavka.yandex.ru/213/product/product-id',
  },
];

export interface ValidationError {
  line: number;
  url: string;
  error: string;
  suggestion?: string;
}

export interface ValidationResult {
  url: string;
  isValid: boolean;
  retailer: RetailerConfig | null;
  error?: string;
  suggestion?: string;
}

export interface BulkValidationResult {
  valid: ValidationResult[];
  invalid: ValidationError[];
  total: number;
  validCount: number;
  invalidCount: number;
}

/**
 * Check if a string is a valid URL
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * Detect retailer from URL domain
 */
export function detectRetailer(url: string): RetailerConfig | null {
  const lowerUrl = url.toLowerCase();

  for (const retailer of SUPPORTED_RETAILERS) {
    for (const pattern of retailer.patterns) {
      if (pattern.test(lowerUrl)) {
        return retailer;
      }
    }
  }

  return null;
}

/**
 * Validate URL format for a specific retailer
 */
export function validateRetailerUrl(url: string, retailer: RetailerConfig): boolean {
  for (const pattern of retailer.urlPatterns) {
    if (pattern.test(url)) {
      return true;
    }
  }
  return false;
}

/**
 * Validate a single URL and return detailed result
 */
export function validateUrl(url: string): ValidationResult {
  const trimmedUrl = url.trim();

  // Empty URL
  if (!trimmedUrl) {
    return {
      url: trimmedUrl,
      isValid: false,
      retailer: null,
      error: 'URL is empty',
    };
  }

  // Check URL format
  if (!isValidUrl(trimmedUrl)) {
    return {
      url: trimmedUrl,
      isValid: false,
      retailer: null,
      error: 'Invalid URL format',
      suggestion: 'Make sure the URL starts with https://',
    };
  }

  // Detect retailer
  const retailer = detectRetailer(trimmedUrl);

  if (!retailer) {
    const supportedList = SUPPORTED_RETAILERS.map(r => r.name).join(', ');
    return {
      url: trimmedUrl,
      isValid: false,
      retailer: null,
      error: 'Unsupported retailer',
      suggestion: `Supported retailers: ${supportedList}`,
    };
  }

  // Validate URL format for retailer
  if (!validateRetailerUrl(trimmedUrl, retailer)) {
    return {
      url: trimmedUrl,
      isValid: false,
      retailer,
      error: `Invalid ${retailer.name} product URL format`,
      suggestion: `Example: ${retailer.exampleUrl}`,
    };
  }

  return {
    url: trimmedUrl,
    isValid: true,
    retailer,
  };
}

/**
 * Validate multiple URLs (bulk validation)
 */
export function validateUrls(input: string): BulkValidationResult {
  const lines = input
    .split('\n')
    .map((line, index) => ({ line: index + 1, url: line.trim() }))
    .filter(({ url }) => url.length > 0);

  const valid: ValidationResult[] = [];
  const invalid: ValidationError[] = [];

  for (const { line, url } of lines) {
    const result = validateUrl(url);

    if (result.isValid) {
      valid.push(result);
    } else {
      invalid.push({
        line,
        url,
        error: result.error || 'Unknown error',
        suggestion: result.suggestion,
      });
    }
  }

  return {
    valid,
    invalid,
    total: lines.length,
    validCount: valid.length,
    invalidCount: invalid.length,
  };
}

/**
 * Get retailer name from URL (convenience function)
 */
export function getRetailerName(url: string): string | null {
  const retailer = detectRetailer(url);
  return retailer?.name || null;
}

/**
 * Get retailer code from URL (convenience function)
 */
export function getRetailerCode(url: string): string | null {
  const retailer = detectRetailer(url);
  return retailer?.code || null;
}

/**
 * Check if URL is from a supported retailer
 */
export function isSupportedRetailer(url: string): boolean {
  return detectRetailer(url) !== null;
}

/**
 * Get list of supported retailer names
 */
export function getSupportedRetailerNames(): string[] {
  return SUPPORTED_RETAILERS.map(r => r.name);
}

/**
 * Format validation errors for display
 */
export function formatValidationErrors(errors: ValidationError[]): string {
  return errors
    .map(err => `Line ${err.line}: ${err.error}${err.suggestion ? ` (${err.suggestion})` : ''}`)
    .join('\n');
}
