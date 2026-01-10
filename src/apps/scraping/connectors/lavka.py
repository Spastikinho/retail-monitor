"""
Yandex Lavka connector - scrapes product data from lavka.yandex.ru.
"""
import json
import re
from datetime import datetime
from typing import Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .base import BaseConnector, ScrapeResult, PriceData, ReviewData
from ..browser import BrowserManager


class LavkaConnector(BaseConnector):
    """Connector for Yandex Lavka."""

    retailer_slug = 'lavka'
    requires_auth = False

    # Pattern: https://lavka.yandex.ru/213/good/name-slug
    PRODUCT_URL_PATTERN = re.compile(r'lavka\.yandex\.ru/\d+/good/([a-zA-Z0-9_-]+)')

    # Selectors for Yandex Lavka product page
    SELECTORS = {
        'title': 'h1[class*="title"], [data-testid="product-title"], .product-title',
        'price_current': '[class*="price-current"], [class*="actual-price"], [data-testid="price"]',
        'price_old': '[class*="price-old"], [class*="crossed-price"], [data-testid="old-price"]',
        'rating': '[class*="rating"], [data-testid="rating"]',
        'reviews_count': '[class*="reviews"], [data-testid="reviews-count"]',
        'in_stock': 'button[class*="add-to-cart"]:not([disabled]), button[class*="buy"]:not([disabled])',
        'out_of_stock': '[class*="out-of-stock"], [class*="unavailable"], [class*="sold-out"]',
        'weight': '[class*="weight"], [class*="volume"], [data-testid="weight"]',
        # Reviews
        'reviews_container': '[class*="reviews-list"], [class*="Reviews"]',
        'review_item': '[class*="review-item"], [class*="Review"]',
        'load_more_reviews': 'button:has-text("Показать ещё"), button:has-text("Ещё")',
    }

    async def scrape_product(self, url: str, browser_manager: BrowserManager = None) -> ScrapeResult:
        """
        Scrape product data from Yandex Lavka.

        Args:
            url: Product page URL
            browser_manager: BrowserManager instance

        Returns:
            ScrapeResult with price and review data
        """
        self.logger.info(f'Scraping Yandex Lavka product: {url}')

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
        response = await page.goto(url, wait_until='domcontentloaded')
        raw_data['status_code'] = response.status if response else None

        if response and response.status != 200:
            return ScrapeResult(
                success=False,
                error_message=f'HTTP {response.status}',
                raw_data=raw_data,
            )

        # Wait for page to load (Lavka uses heavy JS)
        await page.wait_for_timeout(4000)

        # Try to extract from Apollo/Redux state
        app_data = await self._try_extract_app_data(page)
        if app_data:
            raw_data['app_data'] = app_data

        # Extract price data from DOM
        price_data = await self._extract_price_data(page, app_data)
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

    async def _try_extract_app_data(self, page: Page) -> Optional[dict]:
        """Try to get data from page's app state (Apollo/Redux)."""
        try:
            # Try to find Apollo state
            apollo_state = await page.evaluate('''() => {
                // Check for Apollo cache
                if (window.__APOLLO_STATE__) {
                    return window.__APOLLO_STATE__;
                }
                // Check for Next.js data
                const nextData = document.getElementById('__NEXT_DATA__');
                if (nextData) {
                    try {
                        return JSON.parse(nextData.textContent);
                    } catch(e) {}
                }
                // Check for initial state script
                const scripts = document.querySelectorAll('script');
                for (const script of scripts) {
                    const text = script.textContent || '';
                    if (text.includes('__INITIAL_STATE__') || text.includes('window.__STATE__')) {
                        const match = text.match(/window\\.__\\w+__\\s*=\\s*(\\{.+\\})/);
                        if (match) {
                            try {
                                return JSON.parse(match[1]);
                            } catch(e) {}
                        }
                    }
                }
                return null;
            }''')

            if apollo_state:
                return apollo_state

        except Exception as e:
            self.logger.debug(f'Failed to extract app data: {e}')

        return None

    async def _extract_price_data(self, page: Page, app_data: Optional[dict] = None) -> PriceData:
        """Extract price, rating, and stock info from page."""
        data = PriceData()

        # Try to parse app data first
        if app_data:
            parsed = self._parse_app_data(app_data)
            if parsed.price_final:
                return parsed

        # Fallback to DOM extraction
        # Title
        try:
            title_el = await page.query_selector(self.SELECTORS['title'])
            if title_el:
                data.title = (await title_el.inner_text()).strip()
        except Exception as e:
            self.logger.debug(f'Failed to extract title: {e}')

        # Current price
        try:
            price_el = await page.query_selector(self.SELECTORS['price_current'])
            if price_el:
                price_text = await price_el.inner_text()
                data.price_regular = self.parse_price(price_text)
        except Exception as e:
            self.logger.debug(f'Failed to extract current price: {e}')

        # Old price (if on sale)
        try:
            old_price_el = await page.query_selector(self.SELECTORS['price_old'])
            if old_price_el:
                old_price_text = await old_price_el.inner_text()
                old_price = self.parse_price(old_price_text)
                if old_price and data.price_regular and old_price > data.price_regular:
                    data.price_promo = data.price_regular
                    data.price_regular = old_price
        except Exception as e:
            self.logger.debug(f'Failed to extract old price: {e}')

        # Calculate final price
        valid_prices = [p for p in [data.price_regular, data.price_promo] if p]
        data.price_final = min(valid_prices) if valid_prices else None

        # Rating
        try:
            rating_el = await page.query_selector(self.SELECTORS['rating'])
            if rating_el:
                rating_text = await rating_el.inner_text()
                data.rating_avg = self.parse_rating(rating_text)
        except Exception as e:
            self.logger.debug(f'Failed to extract rating: {e}')

        # Reviews count
        try:
            reviews_el = await page.query_selector(self.SELECTORS['reviews_count'])
            if reviews_el:
                reviews_text = await reviews_el.inner_text()
                data.reviews_count = self.parse_reviews_count(reviews_text)
        except Exception as e:
            self.logger.debug(f'Failed to extract reviews count: {e}')

        # In stock check
        try:
            out_of_stock = await page.query_selector(self.SELECTORS['out_of_stock'])
            if out_of_stock:
                data.in_stock = False
            else:
                in_stock = await page.query_selector(self.SELECTORS['in_stock'])
                data.in_stock = in_stock is not None
        except Exception as e:
            self.logger.debug(f'Failed to check stock: {e}')

        return data

    def _parse_app_data(self, app_data: dict) -> PriceData:
        """Parse product data from app state."""
        data = PriceData()

        try:
            # Try to find product in Apollo cache
            if isinstance(app_data, dict):
                # Look for product object in cache
                for key, value in app_data.items():
                    if isinstance(value, dict):
                        if 'title' in value or 'name' in value:
                            data.title = value.get('title') or value.get('name', '')

                        if 'price' in value:
                            price_obj = value['price']
                            if isinstance(price_obj, dict):
                                regular = price_obj.get('value') or price_obj.get('regular')
                                if regular:
                                    data.price_regular = self.parse_price(str(regular))
                                promo = price_obj.get('discount') or price_obj.get('promo')
                                if promo:
                                    data.price_promo = self.parse_price(str(promo))
                            elif isinstance(price_obj, (int, float)):
                                data.price_regular = self.parse_price(str(price_obj))

                        if 'rating' in value:
                            rating_obj = value['rating']
                            if isinstance(rating_obj, dict):
                                data.rating_avg = rating_obj.get('value')
                                data.reviews_count = rating_obj.get('count')
                            elif isinstance(rating_obj, (int, float)):
                                data.rating_avg = float(rating_obj)

                        if 'inStock' in value:
                            data.in_stock = bool(value['inStock'])

                        # If we found meaningful data, calculate final and return
                        if data.price_regular:
                            valid_prices = [p for p in [data.price_regular, data.price_promo] if p]
                            data.price_final = min(valid_prices) if valid_prices else None
                            return data

        except Exception as e:
            self.logger.debug(f'Failed to parse app data: {e}')

        return data

    def parse_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from Lavka URL."""
        match = self.PRODUCT_URL_PATTERN.search(url)
        return match.group(1) if match else None

    async def scrape_reviews(
        self,
        url: str,
        browser_manager: BrowserManager = None,
        max_reviews: int = 50,
    ) -> list[ReviewData]:
        """
        Scrape reviews for a product.

        Note: Yandex Lavka has limited review functionality,
        so this may return fewer reviews than requested.

        Args:
            url: Product page URL
            browser_manager: BrowserManager instance
            max_reviews: Maximum number of reviews to collect

        Returns:
            List of ReviewData objects
        """
        self.logger.info(f'Scraping Yandex Lavka reviews: {url}')

        own_browser = False
        if browser_manager is None:
            browser_manager = BrowserManager()
            await browser_manager.start()
            own_browser = True

        try:
            async with browser_manager.new_page(cookies=self.cookies) as page:
                return await self._scrape_reviews_page(page, url, max_reviews)
        except PlaywrightTimeout as e:
            self.logger.error(f'Timeout scraping reviews {url}: {e}')
            return []
        except Exception as e:
            self.logger.exception(f'Error scraping reviews {url}: {e}')
            return []
        finally:
            if own_browser:
                await browser_manager.stop()

    async def _scrape_reviews_page(
        self,
        page: Page,
        url: str,
        max_reviews: int,
    ) -> list[ReviewData]:
        """Internal method to scrape reviews from page."""
        reviews = []

        # Navigate to product page
        response = await page.goto(url, wait_until='domcontentloaded')
        if not response or response.status != 200:
            return reviews

        await page.wait_for_timeout(4000)

        # Scroll to reviews section
        try:
            reviews_container = await page.query_selector(self.SELECTORS['reviews_container'])
            if reviews_container:
                await reviews_container.scroll_into_view_if_needed()
                await page.wait_for_timeout(1500)
        except Exception as e:
            self.logger.debug(f'Could not scroll to reviews: {e}')

        # Load more reviews
        await self._scroll_to_load_reviews(page, max_reviews)

        # Extract reviews
        review_elements = await page.query_selector_all(self.SELECTORS['review_item'])
        self.logger.info(f'Found {len(review_elements)} review elements')

        for idx, element in enumerate(review_elements[:max_reviews]):
            try:
                review = await self._extract_single_review(element, idx)
                if review:
                    reviews.append(review)
            except Exception as e:
                self.logger.debug(f'Failed to extract review {idx}: {e}')

        return reviews

    async def _scroll_to_load_reviews(self, page: Page, max_reviews: int):
        """Load more reviews by scrolling/clicking."""
        max_attempts = (max_reviews // 10) + 3

        for _ in range(max_attempts):
            review_elements = await page.query_selector_all(self.SELECTORS['review_item'])
            if len(review_elements) >= max_reviews:
                break

            # Try to click "Load more" button
            try:
                load_more = await page.query_selector(self.SELECTORS['load_more_reviews'])
                if load_more:
                    await load_more.click()
                    await page.wait_for_timeout(1500)
                    continue
            except Exception:
                pass

            # Scroll to trigger lazy loading
            await page.evaluate('window.scrollBy(0, 800)')
            await page.wait_for_timeout(800)

    async def _extract_single_review(self, element, index: int) -> Optional[ReviewData]:
        """Extract data from a single review element."""
        element_html = await element.inner_html()
        external_id = f'lavka_review_{hash(element_html) % 10**10}'

        # Extract rating
        rating = await self._extract_review_rating(element)
        if not rating:
            rating = 5

        # Extract text
        text = ''
        try:
            text_el = await element.query_selector('[class*="text"], [class*="comment"], [class*="body"]')
            if text_el:
                text = (await text_el.inner_text()).strip()
        except Exception:
            pass

        if not text:
            try:
                text = await element.inner_text()
                lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 15]
                text = '\n'.join(lines[:5])
            except Exception:
                pass

        if not text:
            return None

        # Extract author
        author_name = ''
        try:
            author_el = await element.query_selector('[class*="author"], [class*="name"]')
            if author_el:
                author_name = (await author_el.inner_text()).strip()[:100]
        except Exception:
            pass

        # Extract date
        published_at = None
        try:
            date_el = await element.query_selector('[class*="date"], [class*="time"]')
            if date_el:
                date_text = await date_el.inner_text()
                published_at = self._parse_review_date(date_text)
        except Exception:
            pass

        return ReviewData(
            external_id=external_id,
            rating=rating,
            text=text,
            author_name=author_name,
            published_at=published_at,
            raw_data={'index': index},
        )

    async def _extract_review_rating(self, element) -> Optional[int]:
        """Extract rating from review element."""
        try:
            rating_el = await element.query_selector('[class*="rating"], [class*="stars"], [class*="rate"]')
            if rating_el:
                # Try data attribute
                rating_value = await rating_el.get_attribute('data-rating')
                if rating_value:
                    return int(float(rating_value))

                # Count filled stars
                filled_stars = await rating_el.query_selector_all('[class*="filled"], [class*="active"]')
                if filled_stars:
                    return min(len(filled_stars), 5)

                # Try class name
                class_attr = await rating_el.get_attribute('class') or ''
                match = re.search(r'rating-?(\d)', class_attr)
                if match:
                    return int(match.group(1))

                # Try text
                rating_text = await rating_el.inner_text()
                match = re.search(r'(\d)', rating_text)
                if match:
                    return int(match.group(1))
        except Exception:
            pass

        return None

    def _parse_review_date(self, date_text: str) -> Optional[datetime]:
        """Parse review date from text."""
        if not date_text:
            return None

        date_text = date_text.strip().lower()

        if 'сегодня' in date_text:
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if 'вчера' in date_text:
            from datetime import timedelta
            return (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        # Russian months mapping
        months = {
            'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4,
            'май': 5, 'мая': 5, 'июн': 6, 'июл': 7, 'авг': 8,
            'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12,
        }

        try:
            # Try format: "15 января 2024" or "15 янв"
            match = re.search(r'(\d{1,2})\s+([а-яё]+)\.?\s*(\d{4})?', date_text)
            if match:
                day = int(match.group(1))
                month_str = match.group(2)[:3]
                year = int(match.group(3)) if match.group(3) else datetime.now().year
                month = months.get(month_str)
                if month:
                    return datetime(year, month, day)

            # Try format: "15.01.2024"
            match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', date_text)
            if match:
                day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                return datetime(year, month, day)
        except Exception:
            pass

        return None
