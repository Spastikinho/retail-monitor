from django.contrib import admin

from .models import Retailer, RetailerSession


@admin.register(Retailer)
class RetailerAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'requires_auth', 'rate_limit_rpm']
    list_filter = ['is_active', 'requires_auth']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'base_url', 'is_active')
        }),
        ('Коннектор', {
            'fields': ('connector_class', 'product_url_pattern')
        }),
        ('Настройки', {
            'fields': ('requires_auth', 'default_region', 'rate_limit_rpm')
        }),
        ('Системные', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RetailerSession)
class RetailerSessionAdmin(admin.ModelAdmin):
    list_display = ['retailer', 'region_code', 'is_valid', 'last_used_at', 'expires_at']
    list_filter = ['retailer', 'is_valid', 'region_code']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_used_at']

    fieldsets = (
        (None, {
            'fields': ('retailer', 'region_code', 'is_valid')
        }),
        ('Данные сессии', {
            'fields': ('user_agent', 'notes'),
            'description': 'Cookies и localStorage хранятся в зашифрованном виде'
        }),
        ('Время', {
            'fields': ('last_used_at', 'expires_at')
        }),
        ('Системные', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
