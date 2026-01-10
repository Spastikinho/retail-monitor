#!/usr/bin/env python3
"""
Test script to verify scraping connectors work with real URLs.

Usage:
    python scripts/test_scraping.py [--retailer RETAILER] [--url URL]

Examples:
    python scripts/test_scraping.py --retailer ozon --url "https://www.ozon.ru/product/..."
    python scripts/test_scraping.py --retailer wildberries --url "https://www.wildberries.ru/catalog/..."
    python scripts/test_scraping.py --all  # Test with sample URLs for all retailers
"""
import asyncio
import argparse
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from apps.scraping.connectors import (
    get_connector,
    get_available_retailers,
    OzonConnector,
    WildberriesConnector,
    PerekrestokConnector,
)
from apps.scraping.browser import BrowserManager


# Sample test URLs for each retailer
SAMPLE_URLS = {
    'ozon': 'https://www.ozon.ru/product/kofe-molotaya-smesi-100-arabika-1-kg-1526428695/',
    'wildberries': 'https://www.wildberries.ru/catalog/214073924/detail.aspx',
    'perekrestok': 'https://www.perekrestok.ru/cat/180/p/kofe-zerno-paulig-arabica-1000-g-3047070',
}


async def test_connector(retailer: str, url: str, verbose: bool = True) -> dict:
    """
    Test a single connector with a URL.

    Returns dict with test results.
    """
    result = {
        'retailer': retailer,
        'url': url,
        'success': False,
        'error': None,
        'data': None,
    }

    print(f"\n{'='*60}")
    print(f"Testing {retailer.upper()} connector")
    print(f"URL: {url}")
    print('='*60)

    # Get connector class
    connector_cls = get_connector(retailer)
    if not connector_cls:
        result['error'] = f"No connector found for retailer: {retailer}"
        print(f"ERROR: {result['error']}")
        return result

    # Initialize browser and connector
    browser = BrowserManager()
    connector = connector_cls()

    try:
        print("Starting browser...")
        await browser.start()

        print("Scraping product data...")
        scrape_result = await connector.scrape_product(url, browser)

        if scrape_result.success:
            result['success'] = True
            result['data'] = {
                'title': getattr(scrape_result.price_data, 'title', None) if scrape_result.price_data else None,
                'price_regular': float(scrape_result.price_data.price_regular) if scrape_result.price_data and scrape_result.price_data.price_regular else None,
                'price_promo': float(scrape_result.price_data.price_promo) if scrape_result.price_data and scrape_result.price_data.price_promo else None,
                'price_final': float(scrape_result.price_data.price_final) if scrape_result.price_data and scrape_result.price_data.price_final else None,
                'rating': scrape_result.price_data.rating_avg if scrape_result.price_data else None,
                'reviews_count': scrape_result.price_data.reviews_count if scrape_result.price_data else None,
                'in_stock': scrape_result.price_data.in_stock if scrape_result.price_data else None,
            }

            print("\n✅ SUCCESS!")
            print("-" * 40)
            if verbose and result['data']:
                print(f"Title: {result['data']['title']}")
                print(f"Price (regular): {result['data']['price_regular']}")
                print(f"Price (promo): {result['data']['price_promo']}")
                print(f"Price (final): {result['data']['price_final']}")
                print(f"Rating: {result['data']['rating']}")
                print(f"Reviews: {result['data']['reviews_count']}")
                print(f"In Stock: {result['data']['in_stock']}")
        else:
            result['error'] = scrape_result.error_message
            print(f"\n❌ FAILED: {result['error']}")

    except Exception as e:
        result['error'] = str(e)
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\nStopping browser...")
        await browser.stop()

    return result


async def test_all_connectors(verbose: bool = True) -> list[dict]:
    """Test all available connectors with sample URLs."""
    results = []

    for retailer in ['ozon', 'wildberries', 'perekrestok']:
        url = SAMPLE_URLS.get(retailer)
        if url:
            result = await test_connector(retailer, url, verbose)
            results.append(result)
            # Small delay between tests
            await asyncio.sleep(2)

    return results


async def test_reviews(retailer: str, url: str) -> list[dict]:
    """Test review scraping for a connector."""
    print(f"\n{'='*60}")
    print(f"Testing {retailer.upper()} REVIEWS")
    print(f"URL: {url}")
    print('='*60)

    connector_cls = get_connector(retailer)
    if not connector_cls:
        print(f"ERROR: No connector for {retailer}")
        return []

    browser = BrowserManager()
    connector = connector_cls()

    try:
        await browser.start()
        print("Scraping reviews...")
        reviews = await connector.scrape_reviews(url, browser, max_reviews=10)

        print(f"\n✅ Found {len(reviews)} reviews")
        for i, review in enumerate(reviews[:5], 1):
            print(f"\n--- Review {i} ---")
            print(f"Author: {review.author_name}")
            print(f"Rating: {review.rating}")
            print(f"Text: {review.text[:100]}..." if len(review.text) > 100 else f"Text: {review.text}")

        return [
            {
                'author': r.author_name,
                'rating': r.rating,
                'text': r.text[:200],
            }
            for r in reviews
        ]

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        await browser.stop()


def print_summary(results: list[dict]):
    """Print summary of test results."""
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)

    print(f"\nTotal: {total_count}, Success: {success_count}, Failed: {total_count - success_count}")
    print()

    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} {result['retailer']}: ", end="")
        if result['success']:
            title = result['data'].get('title', 'N/A') if result['data'] else 'N/A'
            title = title[:50] + "..." if title and len(title) > 50 else title
            print(f"{title}")
        else:
            print(f"FAILED - {result['error']}")


def main():
    parser = argparse.ArgumentParser(description='Test scraping connectors')
    parser.add_argument('--retailer', '-r', help='Retailer to test (ozon, wildberries, perekrestok)')
    parser.add_argument('--url', '-u', help='URL to scrape')
    parser.add_argument('--all', '-a', action='store_true', help='Test all retailers with sample URLs')
    parser.add_argument('--reviews', action='store_true', help='Also test review scraping')
    parser.add_argument('--quiet', '-q', action='store_true', help='Less verbose output')
    parser.add_argument('--list', '-l', action='store_true', help='List available retailers')

    args = parser.parse_args()

    if args.list:
        print("Available retailers:")
        for retailer in get_available_retailers():
            print(f"  - {retailer}")
        return

    verbose = not args.quiet

    if args.all:
        results = asyncio.run(test_all_connectors(verbose))
        print_summary(results)

    elif args.retailer:
        url = args.url or SAMPLE_URLS.get(args.retailer)
        if not url:
            print(f"ERROR: No URL provided and no sample URL for {args.retailer}")
            print(f"Use --url to specify a URL")
            sys.exit(1)

        result = asyncio.run(test_connector(args.retailer, url, verbose))

        if args.reviews:
            asyncio.run(test_reviews(args.retailer, url))

        sys.exit(0 if result['success'] else 1)

    else:
        print("Usage: python test_scraping.py --retailer RETAILER --url URL")
        print("       python test_scraping.py --all")
        print("\nUse --list to see available retailers")
        print("Use --help for more options")


if __name__ == '__main__':
    main()
