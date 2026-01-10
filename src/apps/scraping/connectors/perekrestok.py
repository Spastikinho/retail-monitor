"""
Perekrestok connector - scrapes product data from perekrestok.ru.
"""
import json
import re
from datetime import datetime
from typing import Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .base import BaseConnector, ScrapeResult, PriceData, ReviewData
from ..browser import BrowserManager


class PerekrestokConnector(BaseConnector):
    """Connector for Perekrestok.ru."""

    retailer_slug = 'perekrestok'
    requires_auth = False

    # Pattern: https://www.perekrestok.ru/cat/123/p/name-456789
    PRODUCT_URL_PATTERN = re.compile(r'perekrestok\.ru/cat/\d+/p/[^/]+-(\d+)')
    PRODUCT_API_URL = 'https://www.perekrestok.ru/api/customer/1.4.1.0/catalog/product/plu{product_id}'

    # Multiple selector fallbacks for resilience against site changes
    SELECTORS = {
        'title': [
            'h1[class*="Title"]',
            '.product-title',
            '[data-testid="product-title"]',
            'h1[class*="product"]',
            '.sc-productCard-title h1',
            'h1',
        ],
        'price_current': [
            '[class*="price-new"]',
            '[class*="Price__new"]',
            '[data-testid="price-current"]',
            '.sc-price-new',
            '[class*="actual-price"]',
            '[class*="currentPrice"]',
        ],
        'price_old': [
            '[class*="price-old"]',
            '[class*="Price__old"]',
            '[data-testid="price-old"]',
            '.sc-price-old',
            '[class*="originalPrice"]',
        ],
        'price_card': [
            '[class*="card-price"]',
            '[class*="loyalty-price"]',
            '[class*="cardPrice"]',
            '[data-testid="card-price"]',
        ],
        'rating': [
            '[class*="rating-value"]',
            '[class*="rating"]',
            '[data-testid="rating"]',
            '.sc-rating',
            '[class*="stars-value"]',
        ],
        'reviews_count': [
            '[class*="reviews-count"]',
            '[data-testid="reviews-count"]',
            '.sc-reviews-count',
            '[class*="reviewCount"]',
            'a[href*="reviews"]',
        ],
        'in_stock': [
            '[class*="add-to-cart"]:not([disabled])',
            'button[class*="Buy"]:not([disabled])',
            '[data-testid="add-to-cart"]',
            '.sc-buy-button:not([disabled])',
        ],
        'out_of_stock': [
            '[class*="out-of-stock"]',
            '[class*="unavailable"]',
            '[class*="soldOut"]',
            '[data-testid="out-of-stock"]',
        ],
        # Reviews
        'reviews_container': [
            '[class*="Reviews"]',
            '[class*="reviews-list"]',
            '[data-testid="reviews-container"]',
            '.sc-reviews',
        ],
        'review_item': [
            '[class*="Review__item"]',
            '[class*="review-card"]',
            '[data-testid="review-item"]',
            '.sc-review-item',
        ],
        'load_more_reviews': [
            'button:has-text("Показать ещё")',
            '[class*="show-more"]',
            '[data-testid="load-more"]',
        ],
    }

    # Indicators that we hit anti-bot protection
    CAPTCHA_INDICATORS = [
        'captcha',
        'robot',
        'заблокирован',
        'blocked',
        'security check',
        'доступ ограничен',
    ]

    async def scrape_product(self, url: str, browser_manager: BrowserManager = None) -> ScrapeResult:
        """
        Scrape product data from Perekrestok.

        Args:
            url: Product page URL
            browser_manager: BrowserManager instance

        Returns:
            ScrapeResult with price and review data
        """
        self.logger.info(f'Scraping Perekrestok product: {url}')

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

    async def _find_element(self, page: Page, selector_key: str):
        """Try multiple selectors until one works."""
        selectors = self.SELECTORS.get(selector_key, [])
        if isinstance(selectors, str):
            selectors = [selectors]
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    return element
            except Exception:
                continue
        return None

    async def _check_captcha(self, page: Page) -> bool:
        """Check if we hit CAPTCHA or anti-bot protection."""
        try:
            page_content = await page.content()
            page_lower = page_content.lower()
            for indicator in self.CAPTCHA_INDICATORS:
                if indicator in page_lower:
                    return True
        except Exception:
            pass
        return False

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

        # Wait for page to load
        await page.wait_for_timeout(3000)

        # Check for anti-bot protection
        if await self._check_captcha(page):
            return ScrapeResult(
                success=False,
                error_message='CAPTCHA or anti-bot protection detected',
                raw_data=raw_data,
            )

        # Try to extract from API response (intercept network)
        api_data = await self._try_extract_api_data(page, url)
        if api_data:
            raw_data['api_data'] = api_data

        # Extract price data from DOM
        price_data = await self._extract_price_data(page, api_data)
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

        # Try to extract structured data
        structured_data = await self._extract_structured_data(page)
        if structured_data:
            raw_data['structured_data'] = structured_data

        return ScrapeResult(
            success=True,
            price_data=price_data,
            raw_data=raw_data,
            scraped_at=datetime.now(),
        )

    async def _try_extract_api_data(self, page: Page, url: str) -> Optional[dict]:
        """Try to get data from page's __NEXT_DATA__ or API."""
        try:
            # Try Next.js data
            next_data = await page.evaluate('''() => {
                const el = document.getElementById('__NEXT_DATA__');
                if (el) {
                    try {
                        return JSON.parse(el.textContent);
                    } catch(e) {}
                }
                return null;
            }''')

            if next_data:
                # Navigate to product data in Next.js structure
                props = next_data.get('props', {}).get('pageProps', {})
                if 'product' in props:
                    return props['product']
                if 'initialState' in props:
                    products = props['initialState'].get('products', {})
                    if products:
                        return list(products.values())[0] if products else None
        except Exception as e:
            self.logger.debug(f'Failed to extract Next.js data: {e}')

        return None

    async def _extract_price_data(self, page: Page, api_data: Optional[dict] = None) -> PriceData:
        """Extract price, rating, and stock info from page."""
        data = PriceData()

        # If we have API data, use it as primary source
        if api_data:
            data = self._parse_api_data(api_data)
            if data.price_final:
                return data

        # Fallback to DOM extraction using multi-selector approach
        # Title
        try:
            title_el = await self._find_element(page, 'title')
            if title_el:
                data.title = (await title_el.inner_text()).strip()
        except Exception as e:
            self.logger.debug(f'Failed to extract title: {e}')

        # Current price
        try:
            price_el = await self._find_element(page, 'price_current')
            if price_el:
                price_text = await price_el.inner_text()
                current_price = self.parse_price(price_text)
                if current_price:
                    data.price_regular = current_price
        except Exception as e:
            self.logger.debug(f'Failed to extract current price: {e}')

        # Old/original price (if on sale)
        try:
            old_price_el = await self._find_element(page, 'price_old')
            if old_price_el:
                old_price_text = await old_price_el.inner_text()
                old_price = self.parse_price(old_price_text)
                if old_price and data.price_regular and old_price > data.price_regular:
                    data.price_promo = data.price_regular
                    data.price_regular = old_price
        except Exception as e:
            self.logger.debug(f'Failed to extract old price: {e}')

        # Card price
        try:
            card_price_el = await self._find_element(page, 'price_card')
            if card_price_el:
                card_price_text = await card_price_el.inner_text()
                data.price_card = self.parse_price(card_price_text)
        except Exception as e:
            self.logger.debug(f'Failed to extract card price: {e}')

        # Calculate final price
        valid_prices = [p for p in [data.price_regular, data.price_promo, data.price_card] if p]
        data.price_final = min(valid_prices) if valid_prices else None

        # Rating
        try:
            rating_el = await self._find_element(page, 'rating')
            if rating_el:
                rating_text = await rating_el.inner_text()
                data.rating_avg = self.parse_rating(rating_text)
        except Exception as e:
            self.logger.debug(f'Failed to extract rating: {e}')

        # Reviews count
        try:
            reviews_el = await self._find_element(page, 'reviews_count')
            if reviews_el:
                reviews_text = await reviews_el.inner_text()
                data.reviews_count = self.parse_reviews_count(reviews_text)
        except Exception as e:
            self.logger.debug(f'Failed to extract reviews count: {e}')

        # In stock check
        try:
            out_of_stock = await self._find_element(page, 'out_of_stock')
            if out_of_stock:
                data.in_stock = False
            else:
                in_stock = await self._find_element(page, 'in_stock')
                data.in_stock = in_stock is not None
        except Exception as e:
            self.logger.debug(f'Failed to check stock: {e}')

        return data

    def _parse_api_data(self, api_data: dict) -> PriceData:
        """Parse product data from API response."""
        data = PriceData()

        try:
            data.title = api_data.get('title', '') or api_data.get('name', '')

            # Price data
            prices = api_data.get('prices', {}) or api_data.get('price', {})
            if isinstance(prices, dict):
                # Regular price
                regular = prices.get('regular') or prices.get('price')
                if regular:
                    data.price_regular = self.parse_price(str(regular))

                # Promo price
                promo = prices.get('promo') or prices.get('discount') or prices.get('actual')
                if promo:
                    data.price_promo = self.parse_price(str(promo))

                # Card price
                card = prices.get('card') or prices.get('loyalty')
                if card:
                    data.price_card = self.parse_price(str(card))
            elif isinstance(prices, (int, float)):
                data.price_regular = self.parse_price(str(prices))

            # Calculate final
            valid_prices = [p for p in [data.price_regular, data.price_promo, data.price_card] if p]
            data.price_final = min(valid_prices) if valid_prices else None

            # Rating
            rating_data = api_data.get('rating', {}) or api_data.get('reviews', {})
            if isinstance(rating_data, dict):
                data.rating_avg = rating_data.get('value') or rating_data.get('average')
                data.reviews_count = rating_data.get('count') or rating_data.get('total')
            elif isinstance(rating_data, (int, float)):
                data.rating_avg = float(rating_data)

            # Stock
            data.in_stock = api_data.get('inStock', True) or api_data.get('available', True)

        except Exception as e:
            self.logger.debug(f'Failed to parse API data: {e}')

        return data

    async def _extract_structured_data(self, page: Page) -> Optional[dict]:
        """Try to extract JSON-LD structured data from page."""
        try:
            scripts = await page.query_selector_all('script[type="application/ld+json"]')
            for script in scripts:
                content = await script.inner_html()
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and data.get('@type') == 'Product':
                        return data
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'Product':
                                return item
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        return None

    def parse_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from Perekrestok URL."""
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

        Args:
            url: Product page URL
            browser_manager: BrowserManager instance
            max_reviews: Maximum number of reviews to collect

        Returns:
            List of ReviewData objects
        """
        self.logger.info(f'Scraping Perekrestok reviews: {url}')

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

        await page.wait_for_timeout(3000)

        # Scroll to reviews section
        try:
            reviews_container = await self._find_element(page, 'reviews_container')
            if reviews_container:
                await reviews_container.scroll_into_view_if_needed()
                await page.wait_for_timeout(1500)
        except Exception as e:
            self.logger.debug(f'Could not scroll to reviews: {e}')

        # Load more reviews
        await self._scroll_to_load_reviews(page, max_reviews)

        # Extract reviews - try each selector until one works
        review_elements = []
        for selector in self.SELECTORS.get('review_item', []):
            try:
                review_elements = await page.query_selector_all(selector)
                if review_elements:
                    break
            except Exception:
                continue
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
            # Count reviews using multi-selector approach
            review_count = 0
            for selector in self.SELECTORS.get('review_item', []):
                try:
                    review_elements = await page.query_selector_all(selector)
                    if review_elements:
                        review_count = len(review_elements)
                        break
                except Exception:
                    continue

            if review_count >= max_reviews:
                break

            # Try to click "Load more" button using multi-selector
            try:
                load_more = await self._find_element(page, 'load_more_reviews')
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
        external_id = f'perekrestok_review_{hash(element_html) % 10**10}'

        # Extract rating
        rating = await self._extract_review_rating(element)
        if not rating:
            rating = 5

        # Extract text
        text = ''
        try:
            text_el = await element.query_selector('[class*="text"], [class*="comment"], [class*="content"]')
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

        # Extract pros/cons
        pros, cons = await self._extract_pros_cons(element)

        # Extract author
        author_name = ''
        try:
            author_el = await element.query_selector('[class*="author"], [class*="name"], [class*="user"]')
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
            pros=pros,
            cons=cons,
            published_at=published_at,
            raw_data={'index': index},
        )

    async def _extract_review_rating(self, element) -> Optional[int]:
        """Extract rating from review element."""
        try:
            # Check for star rating
            rating_el = await element.query_selector('[class*="rating"], [class*="stars"], [class*="rate"]')
            if rating_el:
                # Try data attribute
                rating_value = await rating_el.get_attribute('data-rating')
                if rating_value:
                    return int(float(rating_value))

                # Count filled stars
                filled_stars = await rating_el.query_selector_all('[class*="filled"], [class*="active"], [class*="full"]')
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

    async def _extract_pros_cons(self, element) -> tuple[str, str]:
        """Extract pros and cons from review element."""
        pros = ''
        cons = ''

        try:
            pros_el = await element.query_selector('[class*="pros"], [class*="advantage"], [class*="plus"]')
            if pros_el:
                pros = (await pros_el.inner_text()).strip()[:500]
        except Exception:
            pass

        try:
            cons_el = await element.query_selector('[class*="cons"], [class*="disadvantage"], [class*="minus"]')
            if cons_el:
                cons = (await cons_el.inner_text()).strip()[:500]
        except Exception:
            pass

        return pros, cons

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
            # Try format: "15 января 2024" or "15 янв. 2024"
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
