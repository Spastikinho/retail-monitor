"""
LLM service for review analysis using OpenAI.
"""
import json
import logging
from dataclasses import dataclass
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of LLM analysis."""
    success: bool
    remove_suggestions: str = ''
    add_packaging_suggestions: str = ''
    add_taste_suggestions: str = ''
    key_positive_themes: list = None
    key_negative_themes: list = None
    competitor_insights: str = ''
    raw_response: dict = None
    model_used: str = ''
    tokens_used: int = 0
    error_message: str = ''

    def __post_init__(self):
        if self.key_positive_themes is None:
            self.key_positive_themes = []
        if self.key_negative_themes is None:
            self.key_negative_themes = []
        if self.raw_response is None:
            self.raw_response = {}


class ReviewAnalyzer:
    """
    Analyzes reviews using OpenAI GPT models.
    """

    # System prompt for own products (negative reviews focus)
    SYSTEM_PROMPT_OWN = """Ты — аналитик отзывов о продуктах питания (сухофрукты, орехи, снеки).
Твоя задача — проанализировать негативные отзывы покупателей и выделить конкретные
предложения по улучшению продукта.

Формат ответа — строго JSON:
{
    "remove_suggestions": "Что следует убрать или изменить в продукте (конкретные проблемы)",
    "add_packaging_suggestions": "Что добавить или изменить в упаковке",
    "add_taste_suggestions": "Что изменить во вкусе или качестве продукта",
    "key_negative_themes": ["тема1", "тема2", "тема3"],
    "key_positive_themes": ["тема1", "тема2"]
}

Правила:
- Выделяй только конкретные, actionable предложения
- Группируй похожие жалобы в одну тему
- Максимум 5 тем в каждом списке
- Если информации недостаточно, оставь пустую строку
- Отвечай на русском языке"""

    # System prompt for competitor products (positive reviews focus)
    SYSTEM_PROMPT_COMPETITOR = """Ты — аналитик отзывов о продуктах питания конкурентов.
Твоя задача — проанализировать позитивные отзывы покупателей и выделить инсайты,
которые можно использовать для улучшения собственных продуктов.

Формат ответа — строго JSON:
{
    "competitor_insights": "Ключевые преимущества конкурента, которые хвалят покупатели",
    "key_positive_themes": ["тема1", "тема2", "тема3"],
    "key_negative_themes": ["тема1", "тема2"]
}

Правила:
- Фокусируйся на том, что нравится покупателям у конкурента
- Выделяй конкретные характеристики продукта
- Максимум 5 тем в каждом списке
- Отвечай на русском языке"""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL or 'gpt-4o-mini'
        self._client = None

    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                logger.error('OpenAI package not installed')
                raise
            except Exception as e:
                logger.error(f'Failed to initialize OpenAI client: {e}')
                raise
        return self._client

    def analyze_reviews(
        self,
        reviews: list[dict],
        is_own_product: bool = True,
        product_name: str = '',
    ) -> AnalysisResult:
        """
        Analyze a batch of reviews.

        Args:
            reviews: List of review dicts with 'text', 'rating', 'pros', 'cons' keys
            is_own_product: True for own products (focus on negative), False for competitors
            product_name: Product name for context

        Returns:
            AnalysisResult with extracted insights
        """
        if not self.api_key:
            return AnalysisResult(
                success=False,
                error_message='OpenAI API key not configured',
            )

        if not reviews:
            return AnalysisResult(
                success=False,
                error_message='No reviews to analyze',
            )

        # Prepare reviews text
        reviews_text = self._format_reviews(reviews, is_own_product)

        # Select appropriate prompt
        system_prompt = self.SYSTEM_PROMPT_OWN if is_own_product else self.SYSTEM_PROMPT_COMPETITOR

        # Build user message
        if is_own_product:
            user_message = f"""Проанализируй следующие негативные отзывы о продукте "{product_name}":

{reviews_text}

Выдели ключевые проблемы и предложения по улучшению."""
        else:
            user_message = f"""Проанализируй следующие позитивные отзывы о продукте конкурента "{product_name}":

{reviews_text}

Выдели ключевые преимущества, которые можно использовать."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message},
                ],
                temperature=0.3,
                max_tokens=1500,
                response_format={'type': 'json_object'},
            )

            # Parse response
            content = response.choices[0].message.content
            parsed = json.loads(content)

            tokens_used = response.usage.total_tokens if response.usage else 0

            return AnalysisResult(
                success=True,
                remove_suggestions=parsed.get('remove_suggestions', ''),
                add_packaging_suggestions=parsed.get('add_packaging_suggestions', ''),
                add_taste_suggestions=parsed.get('add_taste_suggestions', ''),
                key_positive_themes=parsed.get('key_positive_themes', []),
                key_negative_themes=parsed.get('key_negative_themes', []),
                competitor_insights=parsed.get('competitor_insights', ''),
                raw_response=parsed,
                model_used=self.model,
                tokens_used=tokens_used,
            )

        except json.JSONDecodeError as e:
            logger.error(f'Failed to parse LLM response as JSON: {e}')
            return AnalysisResult(
                success=False,
                error_message=f'Invalid JSON response: {e}',
            )
        except Exception as e:
            logger.exception(f'LLM analysis failed: {e}')
            return AnalysisResult(
                success=False,
                error_message=str(e),
            )

    def _format_reviews(self, reviews: list[dict], is_own_product: bool) -> str:
        """Format reviews for LLM input."""
        lines = []

        for i, review in enumerate(reviews[:30], 1):  # Limit to 30 reviews
            rating = review.get('rating', 0)

            # Filter by sentiment
            if is_own_product and rating > 3:
                continue  # Skip positive for own products
            if not is_own_product and rating < 4:
                continue  # Skip negative for competitors

            text = review.get('text', '').strip()
            pros = review.get('pros', '').strip()
            cons = review.get('cons', '').strip()

            if not text and not pros and not cons:
                continue

            lines.append(f"Отзыв {i} (рейтинг {rating}/5):")
            if text:
                lines.append(f"  {text[:500]}")
            if pros:
                lines.append(f"  + {pros[:200]}")
            if cons:
                lines.append(f"  - {cons[:200]}")
            lines.append('')

        return '\n'.join(lines)

    def extract_topics(self, text: str, max_topics: int = 5) -> list[str]:
        """
        Extract key topics from a single review text.

        Args:
            text: Review text
            max_topics: Maximum number of topics to extract

        Returns:
            List of topic strings
        """
        if not self.api_key or not text:
            return []

        prompt = f"""Извлеки до {max_topics} ключевых тем из следующего отзыва.
Ответ — JSON массив строк: ["тема1", "тема2", ...]
Каждая тема — 1-3 слова на русском языке.

Отзыв: {text[:500]}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.2,
                max_tokens=200,
                response_format={'type': 'json_object'},
            )

            content = response.choices[0].message.content
            # Handle both array and object responses
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed[:max_topics]
            elif isinstance(parsed, dict):
                # Try to find array in dict values
                for v in parsed.values():
                    if isinstance(v, list):
                        return v[:max_topics]
            return []

        except Exception as e:
            logger.debug(f'Topic extraction failed: {e}')
            return []

    def generate_summary(
        self,
        product_name: str,
        reviews_stats: dict,
        key_themes: list[str],
    ) -> str:
        """
        Generate a natural language summary of review analysis.

        Args:
            product_name: Product name
            reviews_stats: Dict with 'total', 'positive', 'negative', 'neutral' counts
            key_themes: List of key themes from reviews

        Returns:
            Summary text
        """
        if not self.api_key:
            return ''

        prompt = f"""Напиши краткое резюме (2-3 предложения) об отзывах на продукт.

Продукт: {product_name}
Всего отзывов: {reviews_stats.get('total', 0)}
Позитивных: {reviews_stats.get('positive', 0)}
Негативных: {reviews_stats.get('negative', 0)}
Нейтральных: {reviews_stats.get('neutral', 0)}
Ключевые темы: {', '.join(key_themes[:5])}

Резюме должно быть информативным и объективным, на русском языке."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.5,
                max_tokens=300,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.debug(f'Summary generation failed: {e}')
            return ''
