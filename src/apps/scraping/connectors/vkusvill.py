"""
VkusVill connector - scrapes product data from vkusvill.ru.
"""
import json
import re
from datetime import datetime
from typing import Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .base import BaseConnector, ScrapeResult, PriceData, ReviewData
from ..browser import BrowserManager


class VkusvillConnector(BaseConnector):
    """Connector for VkusVill.ru."""

    retailer_slug = 'vkusvill'
    requires_auth = False

    # Pattern: https://vkusvill.ru/goods/name-12345.html
    PRODUCT_URL_PATTERN = re.compile(r'vkusvill\.ru/goods/[^/]+-(\d+)\.html')
    PRODUCT_URL_TEMPLATE = 'https://vkusvill.ru/goods/{product_id}.html'

    # Selectors for VkusVill product page
    SELECTORS = {
        'title': 'h1.Product__title, .ProductCard__title',
        'price_block': '.Product__price, .ProductCard__price',
        'price_current': '.Price__value, [class*="price-current"]',
        'price_old': '.Price__old, [class*="price-old"]',
        'price_card': '.Price__club, .VVClubPrice',
        'rating': '.Rating__value, [class*="rating-value"]',
        'reviews_count': '.Rating__count, [class*="reviews-count"]',
        'in_stock': '.Product__buy-btn:not([disabled]), .AddToCart:not([disabled])',
        'out_of_stock': '.Product__not-available, [class*="not-available"]',
        # Reviews
        'reviews_tab': '[data-tab="reviews"], .Tabs__item:has-text("Отзывы")',
        'reviews_container': '.Reviews, .ProductReviews',
        'review_item': '.Review, .ProductReview',
        'load_more_reviews': 'button:has-text("Показать ещё"), .Reviews__more',
    }

    async def scrape_product(self, url: str, browser_manager: BrowserManager = None) -> ScrapeResult:
        """
        Scrape product data from VkusVill.

        Args:
            url: Product page URL
            browser_manager: BrowserManager instance

        Returns:
            ScrapeResult with price and review data
        """
        self.logger.info(f'Scraping VkusVill product: {url}')

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

        # Wait for main content
        try:
            await page.wait_for_selector(self.SELECTORS['title'], timeout=10000)
        except PlaywrightTimeout:
            self.logger.warning('Title selector not found, trying alternative extraction')

        # Extract price data
        price_data = await self._extract_price_data(page)
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

    async def _extract_price_data(self, page: Page) -> PriceData:
        """Extract price, rating, and stock info from page."""
        data = PriceData()

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

        # Old/original price (if on sale)
        try:
            old_price_el = await page.query_selector(self.SELECTORS['price_old'])
            if old_price_el:
                old_price_text = await old_price_el.inner_text()
                old_price = self.parse_price(old_price_text)
                if old_price and data.price_regular and old_price > data.price_regular:
                    # Current becomes promo, old becomes regular
                    data.price_promo = data.price_regular
                    data.price_regular = old_price
        except Exception as e:
            self.logger.debug(f'Failed to extract old price: {e}')

        # VV Club card price
        try:
            card_price_el = await page.query_selector(self.SELECTORS['price_card'])
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
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        return None

    def parse_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from VkusVill URL."""
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
        self.logger.info(f'Scraping VkusVill reviews: {url}')

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

        await page.wait_for_timeout(2000)

        # Try to click reviews tab
        try:
            reviews_tab = await page.query_selector(self.SELECTORS['reviews_tab'])
            if reviews_tab:
                await reviews_tab.click()
                await page.wait_for_timeout(1500)
        except Exception as e:
            self.logger.debug(f'Could not click reviews tab: {e}')

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
            await page.evaluate('window.scrollBy(0, 1000)')
            await page.wait_for_timeout(800)

    async def _extract_single_review(self, element, index: int) -> Optional[ReviewData]:
        """Extract data from a single review element."""
        element_html = await element.inner_html()
        external_id = f'vkusvill_review_{hash(element_html) % 10**10}'

        # Extract rating
        rating = await self._extract_review_rating(element)
        if not rating:
            rating = 5

        # Extract text
        text = ''
        try:
            text_el = await element.query_selector('[class*="text"], .Review__text')
            if text_el:
                text = (await text_el.inner_text()).strip()
        except Exception:
            pass

        if not text:
            try:
                text = await element.inner_text()
                lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 20]
                text = '\n'.join(lines[:5])
            except Exception:
                pass

        if not text:
            return None

        # Extract author
        author_name = ''
        try:
            author_el = await element.query_selector('[class*="author"], .Review__author')
            if author_el:
                author_name = (await author_el.inner_text()).strip()[:100]
        except Exception:
            pass

        # Extract date
        published_at = None
        try:
            date_el = await element.query_selector('[class*="date"], .Review__date')
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
            rating_el = await element.query_selector('[class*="rating"], [class*="stars"]')
            if rating_el:
                # Check for rating value in data attribute
                rating_value = await rating_el.get_attribute('data-rating')
                if rating_value:
                    return int(rating_value)

                # Count filled stars
                filled_stars = await rating_el.query_selector_all('[class*="filled"], [class*="active"]')
                if filled_stars:
                    return len(filled_stars)

                # Try to find in text
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

        # Russian months
        months = {
            'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4,
            'май': 5, 'мая': 5, 'июн': 6, 'июл': 7, 'авг': 8,
            'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12,
        }

        try:
            match = re.search(r'(\d{1,2})\s+([а-яё]+)\s*(\d{4})?', date_text)
            if match:
                day = int(match.group(1))
                month_str = match.group(2)[:3]
                year = int(match.group(3)) if match.group(3) else datetime.now().year
                month = months.get(month_str)
                if month:
                    return datetime(year, month, day)
        except Exception:
            pass

        return None
