from django.contrib import admin

from .models import Product, Listing


class ListingInline(admin.TabularInline):
    model = Listing
    extra = 1
    fields = ['retailer', 'external_url', 'is_active', 'last_scraped_at']
    readonly_fields = ['last_scraped_at']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'is_own', 'product_type', 'weight_grams', 'active_listings_count']
    list_filter = ['is_own', 'brand', 'product_type', 'packaging_type']
    search_fields = ['name', 'brand', 'product_type']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [ListingInline]

    fieldsets = (
        (None, {
            'fields': ('name', 'brand', 'is_own')
        }),
        ('Характеристики', {
            'fields': ('product_type', 'packaging_type', 'weight_grams', 'caliber', 'has_pit', 'variety')
        }),
        ('Дополнительно', {
            'fields': ('extra_attrs', 'notes'),
            'classes': ('collapse',)
        }),
        ('Системные', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def active_listings_count(self, obj):
        return obj.active_listings_count
    active_listings_count.short_description = 'Листингов'


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ['product', 'retailer', 'is_active', 'scrape_priority', 'last_scraped_at']
    list_filter = ['retailer', 'is_active', 'product__is_own']
    search_fields = ['product__name', 'product__brand', 'external_url', 'external_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_scraped_at']
    raw_id_fields = ['product']

    fieldsets = (
        (None, {
            'fields': ('product', 'retailer', 'is_active')
        }),
        ('URL и ID', {
            'fields': ('external_url', 'external_id')
        }),
        ('Настройки сбора', {
            'fields': ('scrape_priority', 'last_scraped_at', 'last_scrape_error')
        }),
        ('Системные', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
