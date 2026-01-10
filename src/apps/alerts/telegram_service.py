"""
Telegram notification service for sending alerts.
"""
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramService:
    """
    Service for sending messages via Telegram Bot API.
    """

    def __init__(self):
        self.bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        self.default_chat_id = getattr(settings, 'TELEGRAM_DEFAULT_CHAT_ID', '')
        self._client = None

    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.bot_token)

    def _get_bot(self):
        """Lazy initialization of Telegram bot."""
        if self._client is None:
            if not self.bot_token:
                raise ValueError('TELEGRAM_BOT_TOKEN not configured')

            try:
                import telegram
                self._client = telegram.Bot(token=self.bot_token)
            except ImportError:
                logger.error('python-telegram-bot package not installed')
                raise
        return self._client

    def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = 'HTML',
        disable_notification: bool = False,
    ) -> dict:
        """
        Send a message to a Telegram chat.

        Args:
            text: Message text (supports HTML formatting)
            chat_id: Target chat ID (uses default if not provided)
            parse_mode: Message format (HTML or Markdown)
            disable_notification: Send silently

        Returns:
            dict with success status and message_id or error
        """
        if not self.is_configured:
            return {
                'success': False,
                'error': 'Telegram not configured',
            }

        target_chat = chat_id or self.default_chat_id
        if not target_chat:
            return {
                'success': False,
                'error': 'No chat_id provided and no default configured',
            }

        try:
            import asyncio

            async def _send():
                bot = self._get_bot()
                message = await bot.send_message(
                    chat_id=target_chat,
                    text=text,
                    parse_mode=parse_mode,
                    disable_notification=disable_notification,
                )
                return message

            # Run async function
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # If we're in an async context, use run_coroutine_threadsafe
                import concurrent.futures
                future = asyncio.run_coroutine_threadsafe(_send(), loop)
                message = future.result(timeout=30)
            else:
                message = loop.run_until_complete(_send())

            logger.info(f'Telegram message sent to {target_chat}: {message.message_id}')

            return {
                'success': True,
                'message_id': message.message_id,
                'chat_id': target_chat,
            }

        except Exception as e:
            logger.exception(f'Failed to send Telegram message: {e}')
            return {
                'success': False,
                'error': str(e),
            }

    def send_alert(
        self,
        alert_type: str,
        product_name: str,
        retailer_name: str,
        message: str,
        details: dict,
        chat_id: Optional[str] = None,
    ) -> dict:
        """
        Send a formatted alert message.

        Args:
            alert_type: Type of alert (price_increase, new_negative_review, etc.)
            product_name: Product name
            retailer_name: Retailer name
            message: Alert message
            details: Additional details dict
            chat_id: Target chat ID

        Returns:
            dict with send result
        """
        # Format message based on alert type
        emoji = self._get_alert_emoji(alert_type)
        title = self._get_alert_title(alert_type)

        formatted_text = f"""
{emoji} <b>{title}</b>

<b>Товар:</b> {self._escape_html(product_name)}
<b>Ретейлер:</b> {retailer_name}

{self._escape_html(message)}
""".strip()

        # Add details if present
        if details:
            if 'old_price' in details and 'new_price' in details:
                formatted_text += f"\n\n<b>Было:</b> {details['old_price']} ₽"
                formatted_text += f"\n<b>Стало:</b> {details['new_price']} ₽"
                if 'pct_change' in details:
                    pct = details['pct_change']
                    sign = '+' if pct > 0 else ''
                    formatted_text += f" ({sign}{pct:.1f}%)"

            if 'rating' in details:
                formatted_text += f"\n<b>Рейтинг:</b> {'⭐' * details['rating']}"

            if 'review_text' in details:
                review_preview = details['review_text'][:200]
                if len(details['review_text']) > 200:
                    review_preview += '...'
                formatted_text += f"\n\n<i>\"{self._escape_html(review_preview)}\"</i>"

        return self.send_message(text=formatted_text, chat_id=chat_id)

    def _get_alert_emoji(self, alert_type: str) -> str:
        """Get emoji for alert type."""
        emojis = {
            'price_increase': '📈',
            'price_decrease': '📉',
            'new_negative_review': '😡',
            'new_positive_competitor': '👀',
            'out_of_stock': '❌',
        }
        return emojis.get(alert_type, '🔔')

    def _get_alert_title(self, alert_type: str) -> str:
        """Get title for alert type."""
        titles = {
            'price_increase': 'Рост цены',
            'price_decrease': 'Падение цены',
            'new_negative_review': 'Новый негативный отзыв',
            'new_positive_competitor': 'Позитивный отзыв конкурента',
            'out_of_stock': 'Товар закончился',
        }
        return titles.get(alert_type, 'Оповещение')

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ''
        return (
            text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
        )


# Convenience function for simple usage
def send_telegram_message(text: str, chat_id: Optional[str] = None) -> dict:
    """Send a simple Telegram message."""
    service = TelegramService()
    return service.send_message(text, chat_id)
