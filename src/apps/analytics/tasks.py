"""
Celery tasks for analytics - LLM processing of reviews.
"""
import logging
from datetime import date

from celery import shared_task
from django.db.models import Q

logger = logging.getLogger(__name__)


@shared_task
def process_review_topics(review_id: str):
    """
    Extract topics from a single review using LLM.

    Args:
        review_id: UUID of the ReviewItem
    """
    from apps.scraping.models import ReviewItem
    from .llm_service import ReviewAnalyzer

    try:
        review = ReviewItem.objects.get(pk=review_id)
    except ReviewItem.DoesNotExist:
        logger.error(f'Review {review_id} not found')
        return {'success': False, 'error': 'Review not found'}

    if review.is_processed:
        return {'success': True, 'skipped': True}

    analyzer = ReviewAnalyzer()

    # Extract topics from review text
    text = review.text
    if review.pros:
        text += f'\nДостоинства: {review.pros}'
    if review.cons:
        text += f'\nНедостатки: {review.cons}'

    topics = analyzer.extract_topics(text)

    # Update review
    review.topics = topics
    review.is_processed = True
    review.save(update_fields=['topics', 'is_processed', 'updated_at'])

    return {'success': True, 'topics': topics}


@shared_task
def process_unprocessed_reviews(limit: int = 100):
    """
    Process all unprocessed reviews in batches.

    Args:
        limit: Maximum reviews to process in this batch
    """
    from apps.scraping.models import ReviewItem

    unprocessed = ReviewItem.objects.filter(
        is_processed=False
    ).values_list('id', flat=True)[:limit]

    queued = 0
    for review_id in unprocessed:
        process_review_topics.delay(str(review_id))
        queued += 1

    logger.info(f'Queued {queued} reviews for topic extraction')
    return {'queued': queued}


@shared_task
def generate_listing_analysis(listing_id: str, period_month: str = None):
    """
    Generate LLM analysis for a listing's reviews.

    Args:
        listing_id: UUID of the Listing
        period_month: YYYY-MM-DD string for period (defaults to current month)
    """
    from apps.products.models import Listing
    from apps.scraping.models import ReviewItem
    from .models import ReviewAnalysis
    from .llm_service import ReviewAnalyzer

    try:
        listing = Listing.objects.select_related('product').get(pk=listing_id)
    except Listing.DoesNotExist:
        logger.error(f'Listing {listing_id} not found')
        return {'success': False, 'error': 'Listing not found'}

    # Determine period
    if period_month:
        from datetime import datetime
        period = datetime.strptime(period_month, '%Y-%m-%d').date()
    else:
        period = date.today().replace(day=1)

    # Check if analysis already exists
    existing = ReviewAnalysis.objects.filter(
        listing=listing,
        period_month=period,
        analysis_type=ReviewAnalysis.AnalysisTypeChoices.MONTHLY,
    ).first()

    if existing:
        logger.info(f'Analysis already exists for {listing} @ {period}')
        return {'success': True, 'skipped': True, 'analysis_id': str(existing.pk)}

    # Get reviews for this listing
    reviews = ReviewItem.objects.filter(
        listing=listing,
    ).values('text', 'rating', 'pros', 'cons')

    reviews_list = list(reviews)

    if not reviews_list:
        logger.info(f'No reviews for {listing}')
        return {'success': True, 'skipped': True, 'reason': 'no_reviews'}

    # Run analysis
    analyzer = ReviewAnalyzer()
    is_own = listing.product.is_own

    result = analyzer.analyze_reviews(
        reviews=reviews_list,
        is_own_product=is_own,
        product_name=listing.product.name,
    )

    if not result.success:
        logger.error(f'Analysis failed for {listing}: {result.error_message}')
        return {'success': False, 'error': result.error_message}

    # Save analysis
    analysis = ReviewAnalysis.objects.create(
        listing=listing,
        period_month=period,
        analysis_type=ReviewAnalysis.AnalysisTypeChoices.MONTHLY,
        remove_suggestions=result.remove_suggestions,
        add_packaging_suggestions=result.add_packaging_suggestions,
        add_taste_suggestions=result.add_taste_suggestions,
        key_positive_themes=result.key_positive_themes,
        key_negative_themes=result.key_negative_themes,
        competitor_insights=result.competitor_insights,
        raw_llm_response=result.raw_response,
        model_used=result.model_used,
        tokens_used=result.tokens_used,
    )

    logger.info(f'Created analysis {analysis.pk} for {listing}')
    return {
        'success': True,
        'analysis_id': str(analysis.pk),
        'tokens_used': result.tokens_used,
    }


@shared_task
def generate_all_analyses(period_month: str = None):
    """
    Generate analyses for all listings with reviews.

    Args:
        period_month: YYYY-MM-DD string (defaults to current month)
    """
    from apps.products.models import Listing
    from apps.scraping.models import ReviewItem

    # Get listings with reviews
    listing_ids = ReviewItem.objects.values_list(
        'listing_id', flat=True
    ).distinct()

    queued = 0
    for listing_id in listing_ids:
        generate_listing_analysis.delay(str(listing_id), period_month)
        queued += 1

    logger.info(f'Queued analysis generation for {queued} listings')
    return {'queued': queued}


# Alias for the view
run_analysis_for_all_listings = generate_all_analyses


@shared_task
def generate_product_insights(product_id: str, period_month: str = None):
    """
    Generate aggregated insights for a product across all retailers.

    Args:
        product_id: UUID of the Product
        period_month: YYYY-MM-DD string (defaults to current month)
    """
    from apps.products.models import Product
    from apps.scraping.models import ReviewItem
    from django.db.models import Count, Q
    from .llm_service import ReviewAnalyzer

    try:
        product = Product.objects.prefetch_related('listings').get(pk=product_id)
    except Product.DoesNotExist:
        logger.error(f'Product {product_id} not found')
        return {'success': False, 'error': 'Product not found'}

    listing_ids = product.listings.values_list('id', flat=True)

    # Get all reviews across listings
    reviews = ReviewItem.objects.filter(
        listing_id__in=listing_ids
    ).values('text', 'rating', 'pros', 'cons', 'topics')

    reviews_list = list(reviews)

    if not reviews_list:
        return {'success': True, 'skipped': True, 'reason': 'no_reviews'}

    # Calculate stats
    stats = ReviewItem.objects.filter(
        listing_id__in=listing_ids
    ).aggregate(
        total=Count('id'),
        positive=Count('id', filter=Q(rating=5)),
        neutral=Count('id', filter=Q(rating=4)),
        negative=Count('id', filter=Q(rating__lte=3)),
    )

    # Collect all topics
    all_topics = []
    for review in reviews_list:
        if review.get('topics'):
            all_topics.extend(review['topics'])

    # Count topic frequency
    from collections import Counter
    topic_counts = Counter(all_topics)
    top_topics = [t for t, _ in topic_counts.most_common(10)]

    # Generate summary
    analyzer = ReviewAnalyzer()
    summary = analyzer.generate_summary(
        product_name=product.name,
        reviews_stats=stats,
        key_themes=top_topics,
    )

    return {
        'success': True,
        'product': product.name,
        'stats': stats,
        'top_topics': top_topics,
        'summary': summary,
    }
