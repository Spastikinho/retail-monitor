from django.contrib import admin
from django.contrib import messages

from .models import AlertRule, AlertEvent
from .tasks import deliver_alert_event, deliver_pending_alerts


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'alert_type', 'is_active', 'channel', 'product', 'retailer', 'events_count']
    list_filter = ['is_active', 'alert_type', 'channel']
    search_fields = ['name', 'product__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['product', 'retailer']

    fieldsets = (
        (None, {
            'fields': ('name', 'alert_type', 'is_active')
        }),
        ('Область действия', {
            'fields': ('product', 'retailer'),
            'description': 'Оставьте пустым для применения ко всем товарам/ретейлерам',
        }),
        ('Условия', {
            'fields': ('threshold_pct', 'threshold_rating'),
        }),
        ('Доставка', {
            'fields': ('channel', 'recipients', 'cooldown_hours'),
        }),
        ('Системная информация', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='События')
    def events_count(self, obj):
        return obj.events.count()


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = ['alert_rule', 'listing', 'triggered_at', 'is_delivered', 'delivered_at', 'has_error']
    list_filter = ['is_delivered', 'alert_rule__alert_type', 'alert_rule']
    search_fields = ['message', 'listing__product__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'triggered_at', 'delivered_at']
    raw_id_fields = ['alert_rule', 'listing', 'snapshot']
    date_hierarchy = 'triggered_at'

    actions = ['retry_delivery']

    @admin.display(boolean=True, description='Ошибка')
    def has_error(self, obj):
        return bool(obj.delivery_error)

    @admin.action(description='Повторить доставку')
    def retry_delivery(self, request, queryset):
        # Reset delivery error and queue for delivery
        count = 0
        for event in queryset.filter(is_delivered=False):
            event.delivery_error = ''
            event.save(update_fields=['delivery_error', 'updated_at'])
            deliver_alert_event.delay(str(event.pk))
            count += 1

        self.message_user(
            request,
            f'Поставлено в очередь на доставку: {count} событий',
            messages.SUCCESS
        )


# Add site-wide action to deliver all pending
def deliver_all_pending_alerts(modeladmin, request, queryset):
    """Deliver all pending alert events."""
    deliver_pending_alerts.delay()
    modeladmin.message_user(
        request,
        'Запущена доставка всех ожидающих оповещений',
        messages.SUCCESS
    )


admin.site.add_action(deliver_all_pending_alerts, 'deliver_all_pending_alerts')
