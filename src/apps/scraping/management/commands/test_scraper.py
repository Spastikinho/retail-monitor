"""
Django management command to test scraping connectors.

Usage:
    python manage.py test_scraper --retailer ozon --url "https://..."
    python manage.py test_scraper --all
    python manage.py test_scraper --list
"""
import asyncio
from django.core.management.base import BaseCommand, CommandError

from apps.scraping.connectors import (
    get_connector,
    get_available_retailers,
    CONNECTOR_REGISTRY,
)
from apps.scraping.browser import BrowserManager


# Sample URLs for testing
SAMPLE_URLS = {
    'ozon': 'https://www.ozon.ru/product/kofe-molotaya-smesi-100-arabica-1-kg-1526428695/',
    'wildberries': 'https://www.wildberries.ru/catalog/214073924/detail.aspx',
    'perekrestok': 'https://www.perekrestok.ru/cat/180/p/kofe-zerno-paulig-arabica-1000-g-3047070',
}


class Command(BaseCommand):
    help = 'Test scraping connectors with real URLs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--retailer', '-r',
            type=str,
            help='Retailer to test (ozon, wildberries, perekrestok)',
        )
        parser.add_argument(
            '--url', '-u',
            type=str,
            help='URL to scrape',
        )
        parser.add_argument(
            '--all', '-a',
            action='store_true',
            help='Test all retailers with sample URLs',
        )
        parser.add_argument(
            '--list', '-l',
            action='store_true',
            help='List available retailers',
        )
        parser.add_argument(
            '--reviews',
            action='store_true',
            help='Also test review scraping',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.stdout.write('Available retailers:')
            for retailer in get_available_retailers():
                self.stdout.write(f'  - {retailer}')
            return

        if options['all']:
            asyncio.run(self.test_all())
        elif options['retailer']:
            url = options['url'] or SAMPLE_URLS.get(options['retailer'])
            if not url:
                raise CommandError(
                    f"No URL provided and no sample URL for {options['retailer']}"
                )
            asyncio.run(self.test_connector(
                options['retailer'],
                url,
                test_reviews=options['reviews']
            ))
        else:
            self.stdout.write(
                'Usage: python manage.py test_scraper --retailer RETAILER --url URL\n'
                '       python manage.py test_scraper --all\n'
                '       python manage.py test_scraper --list'
            )

    async def test_connector(self, retailer: str, url: str, test_reviews: bool = False):
        """Test a single connector."""
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(f'Testing {retailer.upper()} connector')
        self.stdout.write(f'URL: {url}')
        self.stdout.write('='*60)

        connector_cls = get_connector(retailer)
        if not connector_cls:
            self.stderr.write(f'ERROR: No connector for {retailer}')
            return False

        browser = BrowserManager()
        connector = connector_cls()

        try:
            self.stdout.write('Starting browser...')
            await browser.start()

            self.stdout.write('Scraping product data...')
            result = await connector.scrape_product(url, browser)

            if result.success:
                self.stdout.write(self.style.SUCCESS('\n✅ SUCCESS!'))
                self.stdout.write('-' * 40)

                if result.price_data:
                    self.stdout.write(f'Title: {result.price_data.title}')
                    self.stdout.write(f'Price (regular): {result.price_data.price_regular}')
                    self.stdout.write(f'Price (promo): {result.price_data.price_promo}')
                    self.stdout.write(f'Price (final): {result.price_data.price_final}')
                    self.stdout.write(f'Rating: {result.price_data.rating_avg}')
                    self.stdout.write(f'Reviews: {result.price_data.reviews_count}')
                    self.stdout.write(f'In Stock: {result.price_data.in_stock}')

                if test_reviews:
                    await self.test_reviews(connector, url, browser)

                return True
            else:
                self.stderr.write(
                    self.style.ERROR(f'\n❌ FAILED: {result.error_message}')
                )
                return False

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'\n❌ ERROR: {e}'))
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.stdout.write('\nStopping browser...')
            await browser.stop()

    async def test_reviews(self, connector, url: str, browser):
        """Test review scraping."""
        self.stdout.write(f'\n{"="*40}')
        self.stdout.write('Testing REVIEWS')
        self.stdout.write('='*40)

        try:
            reviews = await connector.scrape_reviews(url, browser, max_reviews=10)
            self.stdout.write(f'Found {len(reviews)} reviews')

            for i, review in enumerate(reviews[:5], 1):
                self.stdout.write(f'\n--- Review {i} ---')
                self.stdout.write(f'Author: {review.author_name}')
                self.stdout.write(f'Rating: {review.rating}')
                text = review.text[:100] + '...' if len(review.text) > 100 else review.text
                self.stdout.write(f'Text: {text}')

        except Exception as e:
            self.stderr.write(f'Review error: {e}')

    async def test_all(self):
        """Test all connectors."""
        results = []

        for retailer in ['ozon', 'wildberries', 'perekrestok']:
            url = SAMPLE_URLS.get(retailer)
            if url:
                success = await self.test_connector(retailer, url)
                results.append((retailer, success))
                await asyncio.sleep(2)

        # Summary
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write('SUMMARY')
        self.stdout.write('='*60)

        for retailer, success in results:
            status = self.style.SUCCESS('✅') if success else self.style.ERROR('❌')
            self.stdout.write(f'{status} {retailer}')

        success_count = sum(1 for _, s in results if s)
        self.stdout.write(f'\nTotal: {len(results)}, Success: {success_count}')
