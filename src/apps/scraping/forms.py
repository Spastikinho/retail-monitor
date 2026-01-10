"""
Forms for scraping app.
"""
from django import forms
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from .models import ManualImport, MonitoringGroup


class ManualImportForm(forms.ModelForm):
    """Form for manual URL import."""

    urls = forms.CharField(
        label='URLs товаров',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Введите ссылки на товары (по одной на строку)\n\nhttps://www.ozon.ru/product/...\nhttps://www.wildberries.ru/catalog/...\nhttps://www.perekrestok.ru/cat/...',
        }),
        help_text='Поддерживаются: Ozon, Wildberries, Perekrestok, VkusVill, Яндекс.Лавка. Каждая ссылка с новой строки.',
    )

    scrape_reviews = forms.BooleanField(
        label='Собрать отзывы',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Собирать отзывы к товарам (может занять больше времени)',
    )

    class Meta:
        model = ManualImport
        fields = []  # We don't use model fields directly, we parse URLs

    def clean_urls(self):
        """Validate and parse URLs."""
        urls_text = self.cleaned_data.get('urls', '')
        validator = URLValidator()

        # Split by newlines and filter empty
        lines = [line.strip() for line in urls_text.split('\n') if line.strip()]

        if not lines:
            raise ValidationError('Введите хотя бы одну ссылку')

        if len(lines) > 20:
            raise ValidationError('Максимум 20 ссылок за раз')

        valid_urls = []
        errors = []

        for i, line in enumerate(lines, 1):
            try:
                validator(line)
                # Check if it's a supported retailer
                if not self._is_supported_retailer(line):
                    errors.append(f'Строка {i}: Неподдерживаемый магазин')
                else:
                    valid_urls.append(line)
            except ValidationError:
                errors.append(f'Строка {i}: Неверный формат URL')

        if errors:
            raise ValidationError(errors)

        return valid_urls

    def _is_supported_retailer(self, url: str) -> bool:
        """Check if URL is from a supported retailer."""
        url_lower = url.lower()
        supported = [
            'ozon.ru',
            'wildberries.ru',
            'wb.ru',
            'perekrestok.ru',
            'vkusvill.ru',
            'lavka.yandex.ru',
            'eda.yandex.ru/lavka',
        ]
        return any(pattern in url_lower for pattern in supported)


class SingleUrlForm(forms.Form):
    """Simple form for single URL quick import."""

    url = forms.URLField(
        label='URL товара',
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://www.ozon.ru/product/...',
        }),
    )

    def clean_url(self):
        url = self.cleaned_data.get('url', '')
        url_lower = url.lower()

        supported = [
            'ozon.ru',
            'wildberries.ru',
            'wb.ru',
            'perekrestok.ru',
            'vkusvill.ru',
            'lavka.yandex.ru',
        ]

        if not any(pattern in url_lower for pattern in supported):
            raise ValidationError(
                'Неподдерживаемый магазин. Поддерживаются: Ozon, Wildberries, '
                'Perekrestok, VkusVill, Яндекс.Лавка'
            )

        return url


class EnhancedImportForm(forms.Form):
    """Enhanced form with product categorization and monitoring options."""

    urls = forms.CharField(
        label='Ссылки на товары',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Введите ссылки на товары (по одной на строку)',
        }),
        help_text='Поддерживаются: Ozon, Wildberries, Perekrestok, VkusVill, Яндекс.Лавка',
    )

    product_type = forms.ChoiceField(
        label='Тип товара',
        choices=ManualImport.ProductTypeChoices.choices,
        initial=ManualImport.ProductTypeChoices.COMPETITOR,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text='Выберите тип для правильной классификации в отчётах',
    )

    group = forms.ModelChoiceField(
        label='Группа',
        queryset=MonitoringGroup.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Опционально: группа для организации товаров',
    )

    custom_name = forms.CharField(
        label='Своё название',
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Название для отчётов (опционально)',
        }),
        help_text='Если указать, будет использоваться вместо названия с сайта',
    )

    is_recurring = forms.BooleanField(
        label='Ежемесячный мониторинг',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Автоматически собирать данные 1-го числа каждого месяца',
    )

    scrape_reviews = forms.BooleanField(
        label='Собирать отзывы',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Собирать и анализировать отзывы покупателей',
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['group'].queryset = MonitoringGroup.objects.filter(
                user=user
            ).order_by('group_type', 'name')

    def clean_urls(self):
        """Validate and parse URLs."""
        urls_text = self.cleaned_data.get('urls', '')
        validator = URLValidator()

        lines = [line.strip() for line in urls_text.split('\n') if line.strip()]

        if not lines:
            raise ValidationError('Введите хотя бы одну ссылку')

        if len(lines) > 20:
            raise ValidationError('Максимум 20 ссылок за раз')

        valid_urls = []
        errors = []

        supported = [
            'ozon.ru',
            'wildberries.ru',
            'wb.ru',
            'perekrestok.ru',
            'vkusvill.ru',
            'lavka.yandex.ru',
            'eda.yandex.ru/lavka',
        ]

        for i, line in enumerate(lines, 1):
            try:
                validator(line)
                url_lower = line.lower()
                if not any(pattern in url_lower for pattern in supported):
                    errors.append(f'Строка {i}: Неподдерживаемый магазин')
                else:
                    valid_urls.append(line)
            except ValidationError:
                errors.append(f'Строка {i}: Неверный формат URL')

        if errors:
            raise ValidationError(errors)

        return valid_urls


class MonitoringGroupForm(forms.ModelForm):
    """Form for creating/editing monitoring groups."""

    class Meta:
        model = MonitoringGroup
        fields = ['name', 'group_type', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Конкуренты - молоко',
            }),
            'group_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Описание группы (опционально)',
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control form-control-color',
                'type': 'color',
            }),
        }
