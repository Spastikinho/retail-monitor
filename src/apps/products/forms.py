from django import forms

from .models import Product, Listing
from apps.retailers.models import Retailer


class ProductForm(forms.ModelForm):
    """Form for creating/editing products."""

    class Meta:
        model = Product
        fields = [
            'name', 'brand', 'is_own', 'product_type',
            'packaging_type', 'weight_grams', 'caliber',
            'has_pit', 'variety', 'notes',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class ListingForm(forms.ModelForm):
    """Form for adding a listing to a product."""

    class Meta:
        model = Listing
        fields = ['retailer', 'external_url', 'external_id', 'is_active', 'scrape_priority']
        widgets = {
            'external_url': forms.URLInput(attrs={'placeholder': 'https://...'}),
        }

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product

        # Exclude retailers already linked
        if product:
            existing_retailers = product.listings.values_list('retailer_id', flat=True)
            self.fields['retailer'].queryset = Retailer.objects.filter(
                is_active=True
            ).exclude(id__in=existing_retailers)


class ImportForm(forms.Form):
    """Form for importing products from file."""

    file = forms.FileField(
        label='Файл',
        help_text='Excel (.xlsx) или CSV файл с товарами',
        widget=forms.FileInput(attrs={'accept': '.xlsx,.csv'}),
    )

    def clean_file(self):
        file = self.cleaned_data['file']
        filename = file.name.lower()

        if not (filename.endswith('.xlsx') or filename.endswith('.csv')):
            raise forms.ValidationError('Поддерживаются только файлы .xlsx и .csv')

        # Check file size (max 5MB)
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Файл слишком большой (макс. 5 МБ)')

        return file
