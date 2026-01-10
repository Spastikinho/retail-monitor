"""
Email notification service for alerts.
"""
import logging
from typing import Dict, Any, List, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending alert notifications via email.
    """

    def __init__(self):
        self.from_email = settings.DEFAULT_FROM_EMAIL
        self.default_recipients = settings.ALERT_EMAIL_RECIPIENTS

    def send_alert(
        self,
        alert_type: str,
        product_name: str,
        retailer_name: str,
        message: str,
        details: Dict[str, Any],
        recipients: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Send an alert notification via email.

        Args:
            alert_type: Type of alert (price_increase, new_negative_review, etc.)
            product_name: Name of the product
            retailer_name: Name of the retailer
            message: Alert message
            details: Additional details dict
            recipients: List of email addresses (uses default if not provided)

        Returns:
            Dict with success status and any error message
        """
        to_emails = recipients if recipients else self.default_recipients

        if not to_emails:
            logger.warning('No email recipients configured')
            return {'success': False, 'error': 'No recipients configured'}

        try:
            subject = self._get_subject(alert_type, product_name)

            # Prepare context for template
            context = {
                'alert_type': alert_type,
                'alert_type_display': self._get_alert_type_display(alert_type),
                'product_name': product_name,
                'retailer_name': retailer_name,
                'message': message,
                'details': details,
            }

            # Render HTML email
            html_content = render_to_string('alerts/email/alert_notification.html', context)
            text_content = strip_tags(html_content)

            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=to_emails,
            )
            email.attach_alternative(html_content, 'text/html')

            # Send email
            email.send(fail_silently=False)

            logger.info(f'Alert email sent to {to_emails}: {subject}')
            return {'success': True, 'recipients': to_emails}

        except Exception as e:
            error_msg = str(e)
            logger.error(f'Failed to send alert email: {error_msg}')
            return {'success': False, 'error': error_msg}

    def _get_subject(self, alert_type: str, product_name: str) -> str:
        """Get email subject based on alert type."""
        subjects = {
            'price_increase': f'Рост цены: {product_name}',
            'price_decrease': f'Снижение цены: {product_name}',
            'new_negative_review': f'Негативный отзыв: {product_name}',
            'new_positive_competitor': f'Отзыв конкурента: {product_name}',
            'out_of_stock': f'Нет в наличии: {product_name}',
        }
        return f'[Retail Monitor] {subjects.get(alert_type, f"Оповещение: {product_name}")}'

    def _get_alert_type_display(self, alert_type: str) -> str:
        """Get human-readable alert type."""
        displays = {
            'price_increase': 'Рост цены',
            'price_decrease': 'Снижение цены',
            'new_negative_review': 'Негативный отзыв',
            'new_positive_competitor': 'Позитивный отзыв конкурента',
            'out_of_stock': 'Нет в наличии',
        }
        return displays.get(alert_type, alert_type)

    def send_daily_digest(
        self,
        events: List[Dict[str, Any]],
        recipients: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Send a daily digest of alert events.

        Args:
            events: List of event dicts with alert info
            recipients: List of email addresses

        Returns:
            Dict with success status
        """
        to_emails = recipients if recipients else self.default_recipients

        if not to_emails:
            return {'success': False, 'error': 'No recipients configured'}

        if not events:
            return {'success': True, 'skipped': True, 'reason': 'No events to send'}

        try:
            subject = f'[Retail Monitor] Ежедневный отчёт: {len(events)} оповещений'

            context = {
                'events': events,
                'event_count': len(events),
            }

            html_content = render_to_string('alerts/email/daily_digest.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=to_emails,
            )
            email.attach_alternative(html_content, 'text/html')

            email.send(fail_silently=False)

            logger.info(f'Daily digest sent to {to_emails}: {len(events)} events')
            return {'success': True, 'recipients': to_emails, 'event_count': len(events)}

        except Exception as e:
            error_msg = str(e)
            logger.error(f'Failed to send daily digest: {error_msg}')
            return {'success': False, 'error': error_msg}
