"""
Alert views - manage alert rules and view events.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from apps.products.models import Product
from apps.retailers.models import Retailer
from .models import AlertRule, AlertEvent
from .forms import AlertRuleForm


class AlertRuleListView(LoginRequiredMixin, ListView):
    """List all alert rules."""

    model = AlertRule
    template_name = 'alerts/rule_list.html'
    context_object_name = 'rules'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('product', 'retailer')

        # Filter by is_active
        is_active = self.request.GET.get('is_active')
        if is_active == '1':
            queryset = queryset.filter(is_active=True)
        elif is_active == '0':
            queryset = queryset.filter(is_active=False)

        # Filter by alert type
        alert_type = self.request.GET.get('type')
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['alert_types'] = AlertRule.AlertTypeChoices.choices
        context['current_type'] = self.request.GET.get('type', '')
        context['current_is_active'] = self.request.GET.get('is_active', '')
        return context


class AlertRuleDetailView(LoginRequiredMixin, DetailView):
    """View alert rule details with recent events."""

    model = AlertRule
    template_name = 'alerts/rule_detail.html'
    context_object_name = 'rule'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['events'] = self.object.events.select_related(
            'listing__product', 'listing__retailer'
        ).order_by('-triggered_at')[:50]
        return context


class AlertRuleCreateView(LoginRequiredMixin, CreateView):
    """Create a new alert rule."""

    model = AlertRule
    form_class = AlertRuleForm
    template_name = 'alerts/rule_form.html'
    success_url = reverse_lazy('alerts:rule_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Создать правило'
        context['submit_text'] = 'Создать'
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Правило "{form.instance.name}" создано')
        return super().form_valid(form)


class AlertRuleUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an alert rule."""

    model = AlertRule
    form_class = AlertRuleForm
    template_name = 'alerts/rule_form.html'

    def get_success_url(self):
        return reverse_lazy('alerts:rule_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Редактировать правило'
        context['submit_text'] = 'Сохранить'
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Правило "{form.instance.name}" обновлено')
        return super().form_valid(form)


class AlertRuleDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an alert rule."""

    model = AlertRule
    template_name = 'alerts/rule_confirm_delete.html'
    success_url = reverse_lazy('alerts:rule_list')

    def form_valid(self, form):
        messages.success(self.request, f'Правило "{self.object.name}" удалено')
        return super().form_valid(form)


class AlertEventListView(LoginRequiredMixin, ListView):
    """List all alert events."""

    model = AlertEvent
    template_name = 'alerts/event_list.html'
    context_object_name = 'events'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'alert_rule', 'listing__product', 'listing__retailer'
        )

        # Filter by rule
        rule_id = self.request.GET.get('rule')
        if rule_id:
            queryset = queryset.filter(alert_rule_id=rule_id)

        # Filter by delivered status
        delivered = self.request.GET.get('delivered')
        if delivered == '1':
            queryset = queryset.filter(is_delivered=True)
        elif delivered == '0':
            queryset = queryset.filter(is_delivered=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rules'] = AlertRule.objects.all().order_by('name')
        context['current_rule'] = self.request.GET.get('rule', '')
        context['current_delivered'] = self.request.GET.get('delivered', '')
        return context


class AlertEventDetailView(LoginRequiredMixin, DetailView):
    """View alert event details."""

    model = AlertEvent
    template_name = 'alerts/event_detail.html'
    context_object_name = 'event'

    def get_queryset(self):
        return super().get_queryset().select_related(
            'alert_rule', 'listing__product', 'listing__retailer', 'snapshot'
        )
