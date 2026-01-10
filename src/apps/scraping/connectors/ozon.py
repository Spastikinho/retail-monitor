"""
Ozon connector - scrapes product data from ozon.ru.
Updated with robust selectors and anti-detection.
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


class OzonConnector(BaseConnector):
    """Connector for Ozon.ru marketplace."""

    retailer_slug = 'ozon'
    requires_auth = False

    # URL patterns
    PRODUCT_URL_PATTERN = re.compile(r'ozon\.ru/product/[^/]*?-?(\d+)/?')
    PRODUCT_URL_TEMPLATE = 'https://www.ozon.ru/product/{product_id}/'

    # Updated selectors - Ozon uses data-widget attributes heavily
    # Multiple fallback selectors for each element
    SELECTORS = {
        # Title selectors
        'title': [
            'h1[data-widget="webProductHeading"]',
            'h1.tsHeadline550Medium',
            'div[data-widget="webProductHeading"] h1',
            'h1',
        ],
        # Price block
        'price_block': [
            'div[data-widget="webPrice"]',
            'div[data-widget="webSale"]',
            'div.price-block',
            '[class*="PriceBlock"]',
        ],
        # Individual price elements
        'price_current': [
            'div[data-widget="webPrice"] span[class*="price"]:not([style*="line-through"])',
            'div[data-widget="webPrice"] span.c3 span:first-child',
            'span[class*="Price_price"]',
            'span.price',
        ],
        'price_original': [
            'div[data-widget="webPrice"] span[style*="line-through"]',
            'span[class*="Price_originalPrice"]',
            'span.original-price',
        ],
        'price_card': [
            'div[data-widget="webPrice"] [class*="cardPrice"]',
            'span:has-text("с Ozon Картой")',
        ],
        # Rating
        'rating': [
            'div[data-widget="webSingleProductScore"]',
            'div[data-widget="webReviewProductScore"]',
            '[class*="Rating"]',
            'div.rating',
        ],
        'reviews_count': [
            'div[data-widget="webSingleProductScore"] span',
            'div[data-widget="webReviewProductScore"] a',
            'a[href*="reviews"]',
        ],
        # Stock status
        'in_stock': [
            'div[data-widget="webAddToCart"]',
            'button:has-text("В корзину")',
            'button:has-text("Добавить в корзину")',
        ],
        'out_of_stock': [
            'span:has-text("Нет в наличии")',
            'div:has-text("Товар закончился")',
            '[class*="outOfStock"]',
        ],
        # Reviews
        'reviews_container': [
            'div[data-widget="webReviews"]',
            'div[data-widget="webReviewsList"]',
            '[class*="ReviewsList"]',
        ],
        'review_item': [
            'div[data-review-uuid]',
            'div[data-widget="webReviewItem"]',
            '[class*="ReviewItem"]',
            'article[class*="review"]',
        ],
        'load_more_reviews': [
            'button:has-text("Показать ещё")',
            'button:has-text("Показать больше")',
            'a:has-text("Показать ещё")',
        ],
    }

    async def scrape_product(self, url: str, browser_manager: BrowserManager = None) -> ScrapeResult:
        """Scrape product data from Ozon."""
        self.logger.info(f'Scraping Ozon product: {url}')

        own_browser = False
        if browser_manager is None:
            browser_manager = BrowserManager()
            await browser_manager.start()
            own_browser = True

        try:
            async with browser_manager.new_page(cookies=self.cookies) as page:
                return await self._scrape_page(page, url)
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

    async def _scrape_page(self, page: Page, url: str) -> ScrapeResult:
        """Internal method to scrape the page."""
        raw_data = {
            'url': url,
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

        # Wait for page to fully load
        await wait_for_page_load(page)

        # Check for anti-bot challenge
        if await self._check_captcha(page):
            return ScrapeResult(
                success=False,
                error_message='CAPTCHA detected',
                raw_data=raw_data,
            )

        # Human-like scrolling
        await human_like_scroll(page, scroll_count=2)

        # Try to extract from JSON-LD first (most reliable)
        structured_data = await self._extract_structured_data(page)
        if structured_data:
            raw_data['structured_data'] = structured_data

        # Extract price data from page
        price_data = await self._extract_price_data(page, structured_data)

        raw_data['extracted'] = {
            'title': price_data.title,
            'price_regular': float(price_data.price_regular) if price_data.price_regular else None,
            'price_promo': float(price_data.price_promo) if price_data.price_promo else None,
            'price_card': float(price_data.price_card) if price_data.price_card else None,
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

    async def _check_captcha(self, page: Page) -> bool:
        """Check if page shows a CAPTCHA or anti-bot challenge."""
        captcha_indicators = [
            'iframe[src*="captcha"]',
            'div[class*="captcha"]',
            'img[alt*="captcha"]',
            'text="Подтвердите, что вы не робот"',
            'text="Проверка безопасности"',
        ]
        for selector in captcha_indicators:
            try:
                element = await page.query_selector(selector)
                if element:
                    self.logger.warning('CAPTCHA detected on page')
                    return True
            except Exception:
                pass
        return False

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

    async def _extract_price_data(self, page: Page, structured_data: dict = None) -> PriceData:
        """Extract price, rating, and stock info from page."""
        data = PriceData()

        # Title - try structured data first
        if structured_data and structured_data.get('name'):
            data.title = structured_data['name']
        else:
            title_el = await self._find_element(page, self.SELECTORS['title'])
            if title_el:
                try:
                    data.title = await title_el.inner_text()
                    data.title = data.title.strip()
                except Exception:
                    pass

        # Prices - try structured data first
        if structured_data:
            offers = structured_data.get('offers', {})
            if isinstance(offers, list) and offers:
                offers = offers[0]
            if offers.get('price'):
                try:
                    data.price_final = Decimal(str(offers['price']))
                    data.price_regular = data.price_final
                except (ValueError, TypeError):
                    pass

        # Extract prices from page
        if not data.price_final:
            data = await self._extract_prices_from_page(page, data)

        # Rating
        if structured_data and structured_data.get('aggregateRating'):
            rating_data = structured_data['aggregateRating']
            try:
                data.rating_avg = float(rating_data.get('ratingValue', 0))
                data.reviews_count = int(rating_data.get('reviewCount', 0))
            except (ValueError, TypeError):
                pass

        if not data.rating_avg:
            data = await self._extract_rating_from_page(page, data)

        # Stock status
        if structured_data:
            offers = structured_data.get('offers', {})
            if isinstance(offers, list) and offers:
                offers = offers[0]
            availability = offers.get('availability', '')
            data.in_stock = 'InStock' in availability

        if data.in_stock is None:
            data.in_stock = await self._check_in_stock(page)

        return data

    async def _extract_prices_from_page(self, page: Page, data: PriceData) -> PriceData:
        """Extract prices directly from page elements."""
        try:
            # Get price block
            price_block = await self._find_element(page, self.SELECTORS['price_block'])
            if price_block:
                price_text = await price_block.inner_text()
                prices = self._parse_ozon_prices(price_text)

                data.price_regular = prices.get('regular')
                data.price_promo = prices.get('promo')
                data.price_card = prices.get('card')

                # Calculate final price
                valid_prices = [p for p in [data.price_card, data.price_promo, data.price_regular] if p]
                data.price_final = min(valid_prices) if valid_prices else None

        except Exception as e:
            self.logger.debug(f'Failed to extract prices from page: {e}')

        # Alternative: try to get from page state
        if not data.price_final:
            try:
                # Look for price in any span with ruble sign
                price_elements = await page.query_selector_all('span:has-text("₽")')
                for el in price_elements[:5]:  # Check first 5 matches
                    text = await el.inner_text()
                    price = self.parse_price(text)
                    if price and price > 0:
                        if not data.price_regular:
                            data.price_regular = price
                            data.price_final = price
                        break
            except Exception:
                pass

        return data

    async def _extract_rating_from_page(self, page: Page, data: PriceData) -> PriceData:
        """Extract rating from page elements."""
        try:
            rating_el = await self._find_element(page, self.SELECTORS['rating'])
            if rating_el:
                rating_text = await rating_el.inner_text()
                # Look for pattern like "4.8" or "4,8"
                match = re.search(r'(\d[.,]\d)', rating_text)
                if match:
                    data.rating_avg = float(match.group(1).replace(',', '.'))

                # Look for reviews count
                count_match = re.search(r'(\d+)\s*(?:отзыв|оценк)', rating_text, re.I)
                if count_match:
                    data.reviews_count = int(count_match.group(1))
        except Exception as e:
            self.logger.debug(f'Failed to extract rating: {e}')

        return data

    async def _check_in_stock(self, page: Page) -> bool:
        """Check if product is in stock."""
        # Check for out of stock indicators
        out_of_stock = await self._find_element(page, self.SELECTORS['out_of_stock'])
        if out_of_stock:
            return False

        # Check for add to cart button
        add_to_cart = await self._find_element(page, self.SELECTORS['in_stock'])
        return add_to_cart is not None

    def _parse_ozon_prices(self, price_text: str) -> dict:
        """Parse Ozon price block text."""
        result = {}

        # Clean up text
        price_text = price_text.replace('\xa0', ' ').replace('\n', ' ')

        # Find all prices in text
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

        # Deduplicate and sort
        prices = sorted(set(prices))

        if len(prices) == 1:
            result['regular'] = prices[0]
        elif len(prices) == 2:
            result['promo'] = prices[0]
            result['regular'] = prices[1]
        elif len(prices) >= 3:
            result['card'] = prices[0]
            result['promo'] = prices[1]
            result['regular'] = prices[-1]

        # Check for card price indicator
        if 'картой' in price_text.lower() or 'ozon карт' in price_text.lower():
            if len(prices) >= 2 and 'card' not in result:
                result['card'] = prices[0]

        return result

    async def _extract_structured_data(self, page: Page) -> Optional[dict]:
        """Extract JSON-LD structured data from page."""
        try:
            scripts = await page.query_selector_all('script[type="application/ld+json"]')
            for script in scripts:
                try:
                    content = await script.inner_html()
                    data = json.loads(content)

                    # Handle both single object and array
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'Product':
                                return item
                    elif isinstance(data, dict):
                        if data.get('@type') == 'Product':
                            return data
                        # Check for @graph
                        if '@graph' in data:
                            for item in data['@graph']:
                                if isinstance(item, dict) and item.get('@type') == 'Product':
                                    return item
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            self.logger.debug(f'Failed to extract structured data: {e}')
        return None

    def parse_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from Ozon URL."""
        match = self.PRODUCT_URL_PATTERN.search(url)
        return match.group(1) if match else None

    async def scrape_reviews(
        self,
        url: str,
        browser_manager: BrowserManager = None,
        max_reviews: int = 50,
    ) -> List[ReviewData]:
        """Scrape reviews for a product."""
        self.logger.info(f'Scraping Ozon reviews: {url}')

        own_browser = False
        if browser_manager is None:
            browser_manager = BrowserManager()
            await browser_manager.start()
            own_browser = True

        try:
            async with browser_manager.new_page(cookies=self.cookies, block_resources=False) as page:
                return await self._scrape_reviews_page(page, url, max_reviews)
        except Exception as e:
            self.logger.exception(f'Error scraping reviews: {e}')
            return []
        finally:
            if own_browser:
                await browser_manager.stop()

    async def _scrape_reviews_page(
        self,
        page: Page,
        url: str,
        max_reviews: int,
    ) -> List[ReviewData]:
        """Internal method to scrape reviews from page."""
        reviews = []

        # Navigate to product page
        response = await page.goto(url, wait_until='domcontentloaded')
        if not response or response.status != 200:
            return reviews

        await wait_for_page_load(page)

        # Scroll to load content
        await human_like_scroll(page, scroll_count=5)

        # Try to find reviews section
        reviews_container = await self._find_element(page, self.SELECTORS['reviews_container'])

        if reviews_container:
            # Click to expand reviews if needed
            await reviews_container.scroll_into_view_if_needed()

        # Load more reviews
        await self._load_more_reviews(page, max_reviews)

        # Extract reviews
        review_elements = await page.query_selector_all(
            ', '.join(self.SELECTORS['review_item'])
        )

        self.logger.info(f'Found {len(review_elements)} review elements')

        for idx, element in enumerate(review_elements[:max_reviews]):
            try:
                review = await self._extract_single_review(element, idx)
                if review:
                    reviews.append(review)
            except Exception as e:
                self.logger.debug(f'Failed to extract review {idx}: {e}')

        return reviews

    async def _load_more_reviews(self, page: Page, max_reviews: int):
        """Load more reviews by clicking buttons or scrolling."""
        max_attempts = (max_reviews // 10) + 5

        for _ in range(max_attempts):
            # Count current reviews
            review_elements = await page.query_selector_all(
                ', '.join(self.SELECTORS['review_item'])
            )
            if len(review_elements) >= max_reviews:
                break

            # Try to click "Load more"
            clicked = False
            for selector in self.SELECTORS['load_more_reviews']:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        await button.click()
                        await page.wait_for_timeout(1500)
                        clicked = True
                        break
                except Exception:
                    continue

            if not clicked:
                # Scroll to trigger lazy loading
                await page.evaluate('window.scrollBy(0, 800)')
                await page.wait_for_timeout(1000)

    async def _extract_single_review(self, element, index: int) -> Optional[ReviewData]:
        """Extract data from a single review element."""
        try:
            # Get unique ID
            review_id = await element.get_attribute('data-review-uuid')
            if not review_id:
                element_html = await element.inner_html()
                review_id = f'ozon_review_{hash(element_html) % 10**10}'

            # Get full text
            full_text = await element.inner_text()

            # Extract rating
            rating = 5  # Default
            try:
                # Look for star indicators
                stars = await element.query_selector_all('[class*="Star"][class*="Active"], [class*="star"][class*="fill"]')
                if stars:
                    rating = len(stars)
                else:
                    # Try to find rating text
                    rating_match = re.search(r'(\d)\s*(?:из\s*5|звёзд|звезд)', full_text, re.I)
                    if rating_match:
                        rating = int(rating_match.group(1))
            except Exception:
                pass

            # Extract main text
            text = ''
            try:
                # Try to find main comment text
                text_parts = []
                for line in full_text.split('\n'):
                    line = line.strip()
                    # Skip short lines and metadata
                    if len(line) > 30 and not re.match(r'^(\d+\s+\w+\s+\d+|Достоинства|Недостатки|Комментарий):', line):
                        text_parts.append(line)
                text = '\n'.join(text_parts[:3])
            except Exception:
                pass

            if not text and len(full_text) > 50:
                text = full_text[:500]

            if not text:
                return None

            # Extract author
            author_name = ''
            try:
                author_match = re.search(r'^([А-ЯЁа-яё][а-яё]+\s+[А-ЯЁ]\.)', full_text, re.M)
                if author_match:
                    author_name = author_match.group(1)
            except Exception:
                pass

            # Extract date
            published_at = None
            try:
                date_match = re.search(r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s*(\d{4})?', full_text, re.I)
                if date_match:
                    published_at = self._parse_review_date(date_match.group(0))
            except Exception:
                pass

            # Extract pros/cons
            pros, cons = self._extract_pros_cons(full_text)

            return ReviewData(
                external_id=review_id,
                rating=rating,
                text=text,
                author_name=author_name,
                pros=pros,
                cons=cons,
                published_at=published_at,
                raw_data={'index': index},
            )
        except Exception as e:
            self.logger.debug(f'Error extracting review: {e}')
            return None

    def _parse_review_date(self, date_text: str) -> Optional[datetime]:
        """Parse review date from text."""
        if not date_text:
            return None

        months = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12,
        }

        try:
            match = re.search(r'(\d{1,2})\s+(\w+)\s*(\d{4})?', date_text.lower())
            if match:
                day = int(match.group(1))
                month_str = match.group(2)
                year = int(match.group(3)) if match.group(3) else datetime.now().year

                month = months.get(month_str)
                if month:
                    return datetime(year, month, day)
        except Exception:
            pass

        return None

    def _extract_pros_cons(self, text: str) -> tuple:
        """Extract pros and cons from review text."""
        pros = ''
        cons = ''

        # Try to find pros
        pros_match = re.search(r'(?:Достоинства|Плюсы)[:\s]*(.+?)(?:Недостатки|Минусы|Комментарий|$)', text, re.I | re.S)
        if pros_match:
            pros = pros_match.group(1).strip()[:500]

        # Try to find cons
        cons_match = re.search(r'(?:Недостатки|Минусы)[:\s]*(.+?)(?:Комментарий|$)', text, re.I | re.S)
        if cons_match:
            cons = cons_match.group(1).strip()[:500]

        return pros, cons
