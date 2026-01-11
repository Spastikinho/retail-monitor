# Generated migration for ScrapeRun and ManualImport.run field

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('scraping', '0003_add_monitoring_features'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScrapeRun',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('completed_with_errors', 'Completed with errors'), ('failed', 'Failed')], default='pending', max_length=30, verbose_name='Status')),
                ('items_total', models.PositiveIntegerField(default=0, verbose_name='Total items')),
                ('items_completed', models.PositiveIntegerField(default=0, verbose_name='Completed')),
                ('items_failed', models.PositiveIntegerField(default=0, verbose_name='Failed')),
                ('options', models.JSONField(blank=True, default=dict, help_text='Options passed when creating the run', verbose_name='Run options')),
                ('finished_at', models.DateTimeField(blank=True, null=True, verbose_name='Finished at')),
                ('artifact_bucket', models.CharField(blank=True, help_text='S3/R2 bucket name for raw artifacts', max_length=100, verbose_name='Artifact bucket')),
                ('artifact_prefix', models.CharField(blank=True, help_text='Prefix/folder path in bucket', max_length=200, verbose_name='Artifact prefix')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scrape_runs', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Scrape Run',
                'verbose_name_plural': 'Scrape Runs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='manualimport',
            name='run',
            field=models.ForeignKey(blank=True, help_text='Batch run this import belongs to', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='imports', to='scraping.scraperun', verbose_name='Run'),
        ),
    ]
