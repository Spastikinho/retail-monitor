/**
 * Unit Tests for URL Validation Utility
 *
 * Run these tests with: npx tsx src/lib/__tests__/url-validation.test.ts
 * Or integrate with Jest/Vitest for CI
 */

import {
  isValidUrl,
  detectRetailer,
  validateUrl,
  validateUrls,
  validateRetailerUrl,
  isSupportedRetailer,
  getRetailerName,
  getRetailerCode,
  getSupportedRetailerNames,
  SUPPORTED_RETAILERS,
} from '../url-validation';

// Simple test runner
let passed = 0;
let failed = 0;

function test(name: string, fn: () => void) {
  try {
    fn();
    passed++;
    console.log(`  ✓ ${name}`);
  } catch (error) {
    failed++;
    console.log(`  ✗ ${name}`);
    console.log(`    Error: ${error instanceof Error ? error.message : error}`);
  }
}

function expect<T>(actual: T) {
  return {
    toBe(expected: T) {
      if (actual !== expected) {
        throw new Error(`Expected ${JSON.stringify(expected)} but got ${JSON.stringify(actual)}`);
      }
    },
    toEqual(expected: T) {
      if (JSON.stringify(actual) !== JSON.stringify(expected)) {
        throw new Error(`Expected ${JSON.stringify(expected)} but got ${JSON.stringify(actual)}`);
      }
    },
    toBeTruthy() {
      if (!actual) {
        throw new Error(`Expected truthy value but got ${JSON.stringify(actual)}`);
      }
    },
    toBeFalsy() {
      if (actual) {
        throw new Error(`Expected falsy value but got ${JSON.stringify(actual)}`);
      }
    },
    toBeNull() {
      if (actual !== null) {
        throw new Error(`Expected null but got ${JSON.stringify(actual)}`);
      }
    },
    toContain(item: string) {
      if (!Array.isArray(actual) || !actual.includes(item)) {
        throw new Error(`Expected array to contain ${item}`);
      }
    },
    toHaveLength(length: number) {
      if (!Array.isArray(actual) || actual.length !== length) {
        throw new Error(`Expected array length ${length} but got ${Array.isArray(actual) ? actual.length : 'not an array'}`);
      }
    },
  };
}

// Tests
console.log('\n🧪 URL Validation Tests\n');

console.log('isValidUrl:');
test('accepts valid HTTPS URL', () => {
  expect(isValidUrl('https://www.example.com')).toBe(true);
});
test('accepts valid HTTP URL', () => {
  expect(isValidUrl('http://example.com')).toBe(true);
});
test('rejects invalid URL', () => {
  expect(isValidUrl('not-a-url')).toBe(false);
});
test('rejects empty string', () => {
  expect(isValidUrl('')).toBe(false);
});
test('rejects URL without protocol', () => {
  expect(isValidUrl('www.example.com')).toBe(false);
});

console.log('\ndetectRetailer:');
test('detects Ozon', () => {
  expect(detectRetailer('https://www.ozon.ru/product/test-123')?.code).toBe('ozon');
});
test('detects Wildberries', () => {
  expect(detectRetailer('https://www.wildberries.ru/catalog/123/detail.aspx')?.code).toBe('wildberries');
});
test('detects Wildberries (wb.ru)', () => {
  expect(detectRetailer('https://www.wb.ru/catalog/123')?.code).toBe('wildberries');
});
test('detects VkusVill', () => {
  expect(detectRetailer('https://vkusvill.ru/goods/test-123.html')?.code).toBe('vkusvill');
});
test('detects Perekrestok', () => {
  expect(detectRetailer('https://www.perekrestok.ru/cat/123/p/test')?.code).toBe('perekrestok');
});
test('detects Yandex Lavka', () => {
  expect(detectRetailer('https://lavka.yandex.ru/213/product/test')?.code).toBe('yandex-lavka');
});
test('returns null for unsupported retailer', () => {
  expect(detectRetailer('https://www.amazon.com/product/123')).toBeNull();
});
test('returns null for empty string', () => {
  expect(detectRetailer('')).toBeNull();
});

console.log('\nvalidateUrl:');
test('validates correct Ozon URL', () => {
  const result = validateUrl('https://www.ozon.ru/product/test-product-123456789/');
  expect(result.isValid).toBe(true);
  expect(result.retailer?.code).toBe('ozon');
});
test('validates Ozon URL with just ID', () => {
  const result = validateUrl('https://ozon.ru/product/123456789');
  expect(result.isValid).toBe(true);
});
test('validates correct Wildberries URL', () => {
  const result = validateUrl('https://www.wildberries.ru/catalog/123456789/detail.aspx');
  expect(result.isValid).toBe(true);
  expect(result.retailer?.code).toBe('wildberries');
});
test('validates Wildberries URL without detail.aspx', () => {
  const result = validateUrl('https://wildberries.ru/catalog/123456789');
  expect(result.isValid).toBe(true);
});
test('validates correct VkusVill URL', () => {
  const result = validateUrl('https://vkusvill.ru/goods/product-name-12345.html');
  expect(result.isValid).toBe(true);
  expect(result.retailer?.code).toBe('vkusvill');
});
test('rejects invalid URL format', () => {
  const result = validateUrl('not-a-url');
  expect(result.isValid).toBe(false);
  expect(result.error).toBe('Invalid URL format');
});
test('rejects unsupported retailer', () => {
  const result = validateUrl('https://www.amazon.com/product/123');
  expect(result.isValid).toBe(false);
  expect(result.error).toBe('Unsupported retailer');
});
test('rejects empty URL', () => {
  const result = validateUrl('');
  expect(result.isValid).toBe(false);
  expect(result.error).toBe('URL is empty');
});
test('trims whitespace', () => {
  const result = validateUrl('  https://ozon.ru/product/123456789  ');
  expect(result.isValid).toBe(true);
});

console.log('\nvalidateUrls (bulk):');
test('validates multiple URLs', () => {
  const input = `https://ozon.ru/product/test-123456789
https://wildberries.ru/catalog/123456789`;
  const result = validateUrls(input);
  expect(result.validCount).toBe(2);
  expect(result.invalidCount).toBe(0);
  expect(result.total).toBe(2);
});
test('separates valid and invalid URLs', () => {
  const input = `https://ozon.ru/product/test-123456789
not-a-url
https://amazon.com/product/123`;
  const result = validateUrls(input);
  expect(result.validCount).toBe(1);
  expect(result.invalidCount).toBe(2);
});
test('handles empty lines', () => {
  const input = `https://ozon.ru/product/test-123456789

https://wildberries.ru/catalog/123456789

`;
  const result = validateUrls(input);
  expect(result.validCount).toBe(2);
  expect(result.total).toBe(2);
});
test('provides line numbers for errors', () => {
  const input = `https://ozon.ru/product/test-123456789
not-a-url
https://wildberries.ru/catalog/123456789`;
  const result = validateUrls(input);
  expect(result.invalid[0].line).toBe(2);
  expect(result.invalid[0].url).toBe('not-a-url');
});
test('handles empty input', () => {
  const result = validateUrls('');
  expect(result.validCount).toBe(0);
  expect(result.total).toBe(0);
});

console.log('\nisSupportedRetailer:');
test('returns true for Ozon', () => {
  expect(isSupportedRetailer('https://ozon.ru/product/123')).toBe(true);
});
test('returns false for Amazon', () => {
  expect(isSupportedRetailer('https://amazon.com/product/123')).toBe(false);
});

console.log('\ngetRetailerName:');
test('returns Ozon for ozon.ru URL', () => {
  expect(getRetailerName('https://ozon.ru/product/123')).toBe('Ozon');
});
test('returns Wildberries for wildberries.ru URL', () => {
  expect(getRetailerName('https://wildberries.ru/catalog/123')).toBe('Wildberries');
});
test('returns null for unsupported URL', () => {
  expect(getRetailerName('https://amazon.com/product/123')).toBeNull();
});

console.log('\ngetRetailerCode:');
test('returns ozon for ozon.ru URL', () => {
  expect(getRetailerCode('https://ozon.ru/product/123')).toBe('ozon');
});
test('returns wildberries for wb.ru URL', () => {
  expect(getRetailerCode('https://wb.ru/catalog/123')).toBe('wildberries');
});

console.log('\ngetSupportedRetailerNames:');
test('returns all retailer names', () => {
  const names = getSupportedRetailerNames();
  expect(names).toContain('Ozon');
  expect(names).toContain('Wildberries');
  expect(names).toContain('VkusVill');
  expect(names).toContain('Perekrestok');
  expect(names).toContain('Yandex Lavka');
});

console.log('\nSUPPORTED_RETAILERS config:');
test('has 5 supported retailers', () => {
  expect(SUPPORTED_RETAILERS).toHaveLength(5);
});
test('each retailer has required fields', () => {
  for (const retailer of SUPPORTED_RETAILERS) {
    expect(!!retailer.id).toBeTruthy();
    expect(!!retailer.name).toBeTruthy();
    expect(!!retailer.code).toBeTruthy();
    expect(retailer.patterns.length > 0).toBeTruthy();
    expect(retailer.urlPatterns.length > 0).toBeTruthy();
    expect(!!retailer.exampleUrl).toBeTruthy();
  }
});

// Summary
console.log('\n' + '='.repeat(50));
console.log(`\n✅ ${passed} passed`);
if (failed > 0) {
  console.log(`❌ ${failed} failed`);
  process.exit(1);
} else {
  console.log('\n🎉 All tests passed!\n');
}
