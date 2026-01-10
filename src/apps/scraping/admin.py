from django.contrib import admin

from .models import ScrapeSession, SnapshotPrice, SnapshotReview, ReviewItem


@admin.register(ScrapeSession)
class ScrapeSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'status', 'trigger_type', 'retailer',
        'listings_total', 'listings_success', 'listings_failed',
        'started_at', 'finished_at',
    ]
    list_filter = ['status', 'trigger_type', 'retailer']
    readonly_fields = [
        'id', 'created_at', 'updated_at',
        'started_at', 'finished_at',
        'listings_total', 'listings_success', 'listings_failed',
    ]
    date_hierarchy = 'created_at'


@admin.register(SnapshotPrice)
class SnapshotPriceAdmin(admin.ModelAdmin):
    list_display = [
        'listing', 'period_month', 'price_regular', 'price_promo',
        'price_card', 'price_final', 'in_stock', 'rating_avg', 'scraped_at',
    ]
    list_filter = ['period_month', 'in_stock', 'listing__retailer']
    search_fields = ['listing__product__name', 'listing__product__brand']
    readonly_fields = ['id', 'created_at', 'updated_at', 'scraped_at']
    date_hierarchy = 'period_month'
    raw_id_fields = ['listing', 'session']


@admin.register(SnapshotReview)
class SnapshotReviewAdmin(admin.ModelAdmin):
    list_display = [
        'listing', 'period_month',
        'reviews_5_count', 'reviews_4_count', 'reviews_1_3_count',
        'new_reviews_count', 'scraped_at',
    ]
    list_filter = ['period_month', 'listing__retailer']
    search_fields = ['listing__product__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'scraped_at', 'reviews_1_3_count']
    date_hierarchy = 'period_month'
    raw_id_fields = ['listing', 'session']


@admin.register(ReviewItem)
class ReviewItemAdmin(admin.ModelAdmin):
    list_display = [
        'listing', 'rating', 'author_name', 'sentiment',
        'is_processed', 'published_at', 'scraped_at',
    ]
    list_filter = ['rating', 'sentiment', 'is_processed', 'listing__retailer']
    search_fields = ['text', 'author_name', 'listing__product__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'scraped_at']
    raw_id_fields = ['listing']
