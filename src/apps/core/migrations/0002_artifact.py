"""
Migration to create the Artifact model for durable storage.
"""
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_create_admin_user'),
        ('products', '0001_initial'),
        ('scraping', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Artifact',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('storage_key', models.CharField(db_index=True, help_text='Key/path in object storage', max_length=1024, unique=True, verbose_name='Storage Key')),
                ('artifact_type', models.CharField(choices=[
                    ('html_snapshot', 'HTML Snapshot'),
                    ('json_data', 'JSON Data'),
                    ('screenshot', 'Screenshot'),
                    ('excel_export', 'Excel Export'),
                    ('csv_export', 'CSV Export'),
                    ('raw_response', 'Raw Response'),
                    ('other', 'Other'),
                ], db_index=True, default='other', max_length=32, verbose_name='Type')),
                ('content_type', models.CharField(default='application/octet-stream', max_length=128, verbose_name='Content Type')),
                ('size', models.PositiveBigIntegerField(default=0, verbose_name='Size (bytes)')),
                ('sha256', models.CharField(blank=True, help_text='SHA-256 hash for integrity verification', max_length=64, verbose_name='SHA-256 Hash')),
                ('filename', models.CharField(blank=True, max_length=255, verbose_name='Original Filename')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Additional metadata as JSON', verbose_name='Metadata')),
                ('expires_at', models.DateTimeField(blank=True, help_text='Optional expiration date for temporary artifacts', null=True, verbose_name='Expires At')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_artifacts', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('listing', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='artifacts', to='products.listing', verbose_name='Listing')),
                ('manual_import', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='artifacts', to='scraping.manualimport', verbose_name='Manual Import')),
                ('scrape_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='artifacts', to='scraping.scrapesession', verbose_name='Scrape Session')),
            ],
            options={
                'verbose_name': 'Artifact',
                'verbose_name_plural': 'Artifacts',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='artifact',
            index=models.Index(fields=['artifact_type', 'created_at'], name='core_artifa_artifac_idx'),
        ),
        migrations.AddIndex(
            model_name='artifact',
            index=models.Index(fields=['listing', 'artifact_type'], name='core_artifa_listing_idx'),
        ),
        migrations.AddIndex(
            model_name='artifact',
            index=models.Index(fields=['scrape_session', 'artifact_type'], name='core_artifa_scrape__idx'),
        ),
        migrations.AddIndex(
            model_name='artifact',
            index=models.Index(fields=['manual_import', 'artifact_type'], name='core_artifa_manual__idx'),
        ),
    ]
