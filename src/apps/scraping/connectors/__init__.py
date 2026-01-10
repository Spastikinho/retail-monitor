"""
Connectors package - retailer-specific scraping implementations.
"""
from .base import BaseConnector, ScrapeResult, PriceData, ReviewData
from .ozon import OzonConnector
from .wildberries import WildberriesConnector
from .perekrestok import PerekrestokConnector
from .vkusvill import VkusvillConnector
from .lavka import LavkaConnector

# Registry of all available connectors by retailer slug
CONNECTOR_REGISTRY = {
    'ozon': OzonConnector,
    'wildberries': WildberriesConnector,
    'wb': WildberriesConnector,  # Alias
    'perekrestok': PerekrestokConnector,
    'vkusvill': VkusvillConnector,
    'lavka': LavkaConnector,
    'yandex-lavka': LavkaConnector,  # Alias
}


def get_connector(retailer_slug: str) -> type[BaseConnector] | None:
    """Get connector class for a retailer slug."""
    return CONNECTOR_REGISTRY.get(retailer_slug.lower())


def get_available_retailers() -> list[str]:
    """Get list of retailers with available connectors."""
    # Return unique retailer names (excluding aliases)
    return ['ozon', 'wildberries', 'perekrestok', 'vkusvill', 'lavka']


__all__ = [
    'BaseConnector',
    'ScrapeResult',
    'PriceData',
    'ReviewData',
    'OzonConnector',
    'WildberriesConnector',
    'PerekrestokConnector',
    'VkusvillConnector',
    'LavkaConnector',
    'CONNECTOR_REGISTRY',
    'get_connector',
    'get_available_retailers',
]
