"""
Wildberries connector - scrapes product data from wildberries.ru.
Uses both page scraping and API endpoints where available.
"""
import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .base import BaseConnector, ScrapeResult, PriceData, ReviewData
from ..browser import BrowserManager, human_like_scroll, wait_for_page_load

import logging
logger = logging.getLogger(__name__)


class WildberriesConnector(BaseConnector):
    """Connector for Wildberries.ru marketplace."""

    retailer_slug = 'wildberries'
    requires_auth = False

    # URL patterns
    PRODUCT_URL_PATTERN = re.compile(r'wildberries\.ru/catalog/(\d+)/detail')
    PRODUCT_URL_TEMPLATE = 'https://www.wildberries.ru/catalog/{product_id}/detail.aspx'

    # API endpoints (Wildberries has public APIs)
    API_PRODUCT_URL = 'https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={product_id}'
    API_REVIEWS_URL = 'https://feedbacks1.wb.ru/feedbacks/v1/{product_id}'

    # Page selectors
    SELECTORS = {
        'title': [
            'h1.product-page__title',
            'h1[data-tag="product-title"]',
            '.product-page__header h1',
            'h1',
        ],
        'brand': [
            'a.product-page__brand-link',
            '[data-tag="brand-name"]',
            '.brand-link',
        ],
        'price_block': [
            '.price-block',
            '.product-page__price-block',
            '[class*="PriceBlock"]',
        ],
        'price_current': [
            '.price-block__final-price',
            '.price-block__price',
            'ins.price-block__final-price',
        ],
        'price_original': [
            '.price-block__old-price',
            'del.price-block__old-price',
        ],
        'rating': [
            '.product-review__rating',
            '.address-rate-mini',
            '[class*="rating"]',
        ],
        'reviews_count': [
            '.product-review__count-review',
            '.product-page__reviews-count',
        ],
        'in_stock': [
            '.order-block__button',
            'button:has-text("Добавить в корзину")',
            '[data-tag="product-order"]',
        ],
        'out_of_stock': [
            '.sold-out-product',
            'text="Нет в наличии"',
            'text="Товар закончился"',
        ],
        'review_item': [
            '.feedback__item',
            '.comments__item',
            '[class*="FeedbackItem"]',
        ],
    }

    async def scrape_product(self, url: str, browser_manager: BrowserManager = None) -> ScrapeResult:
        """Scrape product data from Wildberries."""
        self.logger.info(f'Scraping Wildberries product: {url}')

        # Extract product ID
        product_id = self.parse_product_id(url)
        if not product_id:
            return ScrapeResult(
                success=False,
                error_message='Could not extract product ID from URL',
                scraped_at=datetime.now(),
            )

        # Try API first (faster and more reliable)
        api_result = await self._scrape_via_api(product_id)
        if api_result.success:
            return api_result

        # Fall back to page scraping
        self.logger.info('API scraping failed, falling back to page scraping')

        own_browser = False
        if browser_manager is None:
            browser_manager = BrowserManager()
            await browser_manager.start()
            own_browser = True

        try:
            async with browser_manager.new_page(cookies=self.cookies) as page:
                return await self._scrape_page(page, url, product_id)
        except PlaywrightTimeout as e:
            self.logger.error(f'Timeout scraping {url}: {e}')
            return ScrapeResult(
                success=False,
                error_message=f'Timeout: {str(e)}',
                scraped_at=datetime.now(),
            )
        except Exception as e:
            self.logger.exception(f'Error scraping {url}: {e}')
            return ScrapeResult(
                success=False,
                error_message=str(e),
                scraped_at=datetime.now(),
            )
        finally:
            if own_browser:
                await browser_manager.stop()

    async def _scrape_via_api(self, product_id: str) -> ScrapeResult:
        """Scrape product data using Wildberries API."""
        import httpx

        raw_data = {
            'product_id': product_id,
            'source': 'api',
            'scraped_at': datetime.now().isoformat(),
        }

        try:
            api_url = self.API_PRODUCT_URL.format(product_id=product_id)

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    api_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/json',
                    },
                )

                if response.status_code != 200:
                    return ScrapeResult(
                        success=False,
                        error_message=f'API returned {response.status_code}',
                        raw_data=raw_data,
                    )

                data = response.json()
                raw_data['api_response'] = data

            # Parse API response
            products = data.get('data', {}).get('products', [])
            if not products:
                return ScrapeResult(
                    success=False,
                    error_message='No product data in API response',
                    raw_data=raw_data,
                )

            product = products[0]

            price_data = PriceData()
            price_data.title = product.get('name', '')

            # Prices in API are in kopecks
            if product.get('sizes'):
                size = product['sizes'][0]
                price_info = size.get('price', {})

                basic_price = price_info.get('basic', 0)
                product_price = price_info.get('product', 0)
                total_price = price_info.get('total', 0)

                # Convert from kopecks
                if basic_price:
                    price_data.price_regular = Decimal(str(basic_price / 100))
                if product_price:
                    price_data.price_promo = Decimal(str(product_price / 100))
                if total_price:
                    price_data.price_final = Decimal(str(total_price / 100))

                if not price_data.price_final:
                    price_data.price_final = price_data.price_promo or price_data.price_regular

            # Rating
            price_data.rating_avg = product.get('reviewRating', 0)
            price_data.reviews_count = product.get('feedbacks', 0)

            # Stock - check if any sizes have stock
            price_data.in_stock = False
            for size in product.get('sizes', []):
                stocks = size.get('stocks', [])
                if stocks and any(s.get('qty', 0) > 0 for s in stocks):
                    price_data.in_stock = True
                    break

            raw_data['extracted'] = {
                'title': price_data.title,
                'price_regular': float(price_data.price_regular) if price_data.price_regular else None,
                'price_promo': float(price_data.price_promo) if price_data.price_promo else None,
                'price_final': float(price_data.price_final) if price_data.price_final else None,
                'rating': price_data.rating_avg,
                'reviews_count': price_data.reviews_count,
                'in_stock': price_data.in_stock,
            }

            return ScrapeResult(
                success=True,
                price_data=price_data,
                raw_data=raw_data,
                scraped_at=datetime.now(),
            )

        except Exception as e:
            self.logger.warning(f'API scraping failed: {e}')
            return ScrapeResult(
                success=False,
                error_message=f'API error: {str(e)}',
                raw_data=raw_data,
            )

    async def _scrape_page(self, page: Page, url: str, product_id: str) -> ScrapeResult:
        """Scrape product data from page."""
        raw_data = {
            'url': url,
            'product_id': product_id,
            'source': 'page',
            'scraped_at': datetime.now().isoformat(),
        }

        # Navigate to product page
        try:
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            raw_data['status_code'] = response.status if response else None
        except PlaywrightTimeout:
            return ScrapeResult(
                success=False,
                error_message='Navigation timeout',
                raw_data=raw_data,
            )

        if response and response.status != 200:
            return ScrapeResult(
                success=False,
                error_message=f'HTTP {response.status}',
                raw_data=raw_data,
            )

        await wait_for_page_load(page)
        await human_like_scroll(page, scroll_count=2)

        price_data = await self._extract_price_data(page)

        raw_data['extracted'] = {
            'title': price_data.title,
            'price_regular': float(price_data.price_regular) if price_data.price_regular else None,
            'price_promo': float(price_data.price_promo) if price_data.price_promo else None,
            'price_final': float(price_data.price_final) if price_data.price_final else None,
            'rating': price_data.rating_avg,
            'reviews_count': price_data.reviews_count,
            'in_stock': price_data.in_stock,
        }

        return ScrapeResult(
            success=True,
            price_data=price_data,
            raw_data=raw_data,
            scraped_at=datetime.now(),
        )

    async def _find_element(self, page: Page, selectors: List[str]):
        """Try multiple selectors and return first matching element."""
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    return element
            except Exception:
                continue
        return None

    async def _extract_price_data(self, page: Page) -> PriceData:
        """Extract price data from page."""
        data = PriceData()

        # Title
        title_el = await self._find_element(page, self.SELECTORS['title'])
        if title_el:
            try:
                data.title = await title_el.inner_text()
                data.title = data.title.strip()
            except Exception:
                pass

        # Brand
        brand_el = await self._find_element(page, self.SELECTORS['brand'])
        if brand_el and data.title:
            try:
                brand = await brand_el.inner_text()
                brand = brand.strip()
                if brand and brand.lower() not in data.title.lower():
                    data.title = f'{brand} {data.title}'
            except Exception:
                pass

        # Prices
        try:
            price_block = await self._find_element(page, self.SELECTORS['price_block'])
            if price_block:
                price_text = await price_block.inner_text()
                prices = self._parse_wb_prices(price_text)
                data.price_regular = prices.get('regular')
                data.price_promo = prices.get('promo')
                data.price_final = prices.get('final') or data.price_promo or data.price_regular
        except Exception as e:
            self.logger.debug(f'Failed to extract prices: {e}')

        # Rating
        try:
            rating_el = await self._find_element(page, self.SELECTORS['rating'])
            if rating_el:
                rating_text = await rating_el.inner_text()
                match = re.search(r'(\d[.,]\d)', rating_text)
                if match:
                    data.rating_avg = float(match.group(1).replace(',', '.'))
        except Exception:
            pass

        # Reviews count
        try:
            reviews_el = await self._find_element(page, self.SELECTORS['reviews_count'])
            if reviews_el:
                reviews_text = await reviews_el.inner_text()
                match = re.search(r'(\d+)', reviews_text.replace(' ', ''))
                if match:
                    data.reviews_count = int(match.group(1))
        except Exception:
            pass

        # Stock status
        out_of_stock = await self._find_element(page, self.SELECTORS['out_of_stock'])
        if out_of_stock:
            data.in_stock = False
        else:
            add_to_cart = await self._find_element(page, self.SELECTORS['in_stock'])
            data.in_stock = add_to_cart is not None

        return data

    def _parse_wb_prices(self, price_text: str) -> dict:
        """Parse Wildberries price text."""
        result = {}
        price_text = price_text.replace('\xa0', ' ').replace('\n', ' ')

        # Find all prices (Wildberries uses ₽ symbol)
        price_matches = re.findall(r'(\d[\d\s]*)\s*₽', price_text)
        prices = []
        for match in price_matches:
            cleaned = match.replace(' ', '')
            if cleaned.isdigit():
                price = Decimal(cleaned)
                if price > 0:
                    prices.append(price)

        if not prices:
            return result

        prices = sorted(set(prices))

        if len(prices) == 1:
            result['final'] = prices[0]
        elif len(prices) >= 2:
            result['final'] = prices[0]  # Lower price is current
            result['regular'] = prices[-1]  # Higher price is original

        return result

    def parse_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from Wildberries URL."""
        match = self.PRODUCT_URL_PATTERN.search(url)
        if match:
            return match.group(1)

        # Alternative: extract from path
        alt_match = re.search(r'/catalog/(\d+)', url)
        if alt_match:
            return alt_match.group(1)

        return None

    async def scrape_reviews(
        self,
        url: str,
        browser_manager: BrowserManager = None,
        max_reviews: int = 50,
    ) -> List[ReviewData]:
        """Scrape reviews using API."""
        product_id = self.parse_product_id(url)
        if not product_id:
            return []

        return await self._scrape_reviews_api(product_id, max_reviews)

    async def _scrape_reviews_api(self, product_id: str, max_reviews: int) -> List[ReviewData]:
        """Scrape reviews using Wildberries feedbacks API."""
        import httpx

        reviews = []

        try:
            # Wildberries uses a different API structure for reviews
            # The product ID needs to be formatted for the API
            vol = int(product_id) // 100000
            part = int(product_id) // 1000

            # Determine basket number based on vol
            if vol >= 0 and vol <= 143:
                basket = '01'
            elif vol >= 144 and vol <= 287:
                basket = '02'
            elif vol >= 288 and vol <= 431:
                basket = '03'
            elif vol >= 432 and vol <= 719:
                basket = '04'
            elif vol >= 720 and vol <= 1007:
                basket = '05'
            elif vol >= 1008 and vol <= 1061:
                basket = '06'
            elif vol >= 1062 and vol <= 1115:
                basket = '07'
            elif vol >= 1116 and vol <= 1169:
                basket = '08'
            elif vol >= 1170 and vol <= 1313:
                basket = '09'
            elif vol >= 1314 and vol <= 1601:
                basket = '10'
            elif vol >= 1602 and vol <= 1655:
                basket = '11'
            elif vol >= 1656 and vol <= 1919:
                basket = '12'
            else:
                basket = '13'

            api_url = f'https://feedbacks{basket}.wb.ru/feedbacks/v1/{product_id}'

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    api_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/json',
                    },
                )

                if response.status_code != 200:
                    self.logger.warning(f'Reviews API returned {response.status_code}')
                    return []

                data = response.json()

            feedbacks = data.get('feedbacks', [])

            for idx, fb in enumerate(feedbacks[:max_reviews]):
                try:
                    review = ReviewData(
                        external_id=fb.get('id', f'wb_{product_id}_{idx}'),
                        rating=fb.get('productValuation', 5),
                        text=fb.get('text', ''),
                        author_name=fb.get('wbUserDetails', {}).get('name', ''),
                        pros=fb.get('pros', ''),
                        cons=fb.get('cons', ''),
                        published_at=self._parse_wb_date(fb.get('createdDate')),
                        raw_data={'index': idx},
                    )
                    if review.text or review.pros or review.cons:
                        reviews.append(review)
                except Exception as e:
                    self.logger.debug(f'Error parsing review: {e}')

            self.logger.info(f'Extracted {len(reviews)} reviews from API')

        except Exception as e:
            self.logger.warning(f'Failed to scrape reviews via API: {e}')

        return reviews

    def _parse_wb_date(self, date_str: str) -> Optional[datetime]:
        """Parse Wildberries date format."""
        if not date_str:
            return None

        try:
            # Format: "2024-01-15T10:30:00Z"
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            pass

        return None
