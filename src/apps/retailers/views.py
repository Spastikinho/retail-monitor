from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView

from .models import Retailer


class RetailerListView(LoginRequiredMixin, ListView):
    """List all retailers."""

    model = Retailer
    template_name = 'retailers/list.html'
    context_object_name = 'retailers'


class RetailerDetailView(LoginRequiredMixin, DetailView):
    """Retailer detail view."""

    model = Retailer
    template_name = 'retailers/detail.html'
    context_object_name = 'retailer'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
