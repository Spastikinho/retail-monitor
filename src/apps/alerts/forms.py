"""
Alert forms for creating and editing alert rules.
"""
from django import forms

from apps.products.models import Product
from apps.retailers.models import Retailer
from .models import AlertRule


class AlertRuleForm(forms.ModelForm):
    """Form for creating/editing alert rules."""

    class Meta:
        model = AlertRule
        fields = [
            'name', 'alert_type', 'is_active',
            'product', 'retailer',
            'threshold_pct', 'threshold_rating',
            'channel', 'recipients', 'cooldown_hours',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'alert_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'retailer': forms.Select(attrs={'class': 'form-select'}),
            'threshold_pct': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'например, 5.00 для 5%',
            }),
            'threshold_rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
            }),
            'channel': forms.Select(attrs={'class': 'form-select'}),
            'recipients': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '["123456789", "@username"]',
            }),
            'cooldown_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make product and retailer optional with empty label
        self.fields['product'].queryset = Product.objects.order_by('name')
        self.fields['product'].empty_label = 'Все товары'
        self.fields['product'].required = False

        self.fields['retailer'].queryset = Retailer.objects.filter(is_active=True).order_by('name')
        self.fields['retailer'].empty_label = 'Все ретейлеры'
        self.fields['retailer'].required = False

        # Set help texts
        self.fields['threshold_pct'].help_text = 'Порог изменения цены в процентах (для алертов на цену)'
        self.fields['threshold_rating'].help_text = 'Порог рейтинга отзыва (для алертов на отзывы)'
        self.fields['recipients'].help_text = 'JSON массив получателей (chat_id или @username)'
        self.fields['cooldown_hours'].help_text = 'Минимальный интервал между оповещениями'

    def clean_recipients(self):
        """Validate recipients JSON."""
        import json
        value = self.cleaned_data.get('recipients')

        if not value:
            return []

        if isinstance(value, list):
            return value

        try:
            parsed = json.loads(value)
            if not isinstance(parsed, list):
                raise forms.ValidationError('Должен быть JSON массив')
            return parsed
        except json.JSONDecodeError:
            raise forms.ValidationError('Некорректный JSON формат')

    def clean(self):
        cleaned_data = super().clean()
        alert_type = cleaned_data.get('alert_type')

        # Validate threshold based on alert type
        if alert_type in ['price_increase', 'price_decrease']:
            if not cleaned_data.get('threshold_pct'):
                self.add_error('threshold_pct', 'Обязательно для алертов на цену')

        if alert_type in ['new_negative_review', 'new_positive_competitor']:
            # Rating threshold is optional, has defaults
            pass

        return cleaned_data
