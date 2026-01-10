"""
Management command to set up initial data (retailers).
"""
from django.core.management.base import BaseCommand

from apps.retailers.models import Retailer


class Command(BaseCommand):
    help = 'Set up initial retailers and demo data'

    def handle(self, *args, **options):
        retailers_data = [
            {
                'name': 'Ozon',
                'slug': 'ozon',
                'base_url': 'https://www.ozon.ru',
                'connector_class': 'apps.scraping.connectors.ozon.OzonConnector',
                'product_url_pattern': r'ozon\.ru/product/[^/]+-(\d+)',
                'requires_auth': False,
                'rate_limit_rpm': 10,
            },
            {
                'name': 'Wildberries',
                'slug': 'wildberries',
                'base_url': 'https://www.wildberries.ru',
                'connector_class': 'apps.scraping.connectors.wildberries.WildberriesConnector',
                'product_url_pattern': r'wildberries\.ru/catalog/(\d+)/detail',
                'requires_auth': False,
                'rate_limit_rpm': 10,
            },
            {
                'name': 'ВкусВилл',
                'slug': 'vkusvill',
                'base_url': 'https://vkusvill.ru',
                'connector_class': 'apps.scraping.connectors.vkusvill.VkusvillConnector',
                'product_url_pattern': r'vkusvill\.ru/goods/[^/]+-(\d+)\.html',
                'requires_auth': False,
                'rate_limit_rpm': 10,
            },
            {
                'name': 'Перекрёсток',
                'slug': 'perekrestok',
                'base_url': 'https://www.perekrestok.ru',
                'connector_class': 'apps.scraping.connectors.perekrestok.PerekrestokConnector',
                'product_url_pattern': r'perekrestok\.ru/cat/\d+/p/[^/]+-(\d+)',
                'requires_auth': False,
                'rate_limit_rpm': 10,
            },
            {
                'name': 'Яндекс Лавка',
                'slug': 'lavka',
                'base_url': 'https://lavka.yandex.ru',
                'connector_class': 'apps.scraping.connectors.lavka.LavkaConnector',
                'product_url_pattern': r'lavka\.yandex\.ru/product/([a-zA-Z0-9_-]+)',
                'requires_auth': False,
                'rate_limit_rpm': 5,
            },
        ]

        created_count = 0
        for data in retailers_data:
            retailer, created = Retailer.objects.update_or_create(
                slug=data['slug'],
                defaults=data,
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created retailer: {retailer.name}'))
            else:
                self.stdout.write(f'Updated retailer: {retailer.name}')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created {created_count} new retailers, updated {len(retailers_data) - created_count}.'
        ))
