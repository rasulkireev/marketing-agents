# Generated by Django 5.1.5 on 2025-02-16 19:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_blogposttitlesuggestion_prompt'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogposttitlesuggestion',
            name='content_type',
            field=models.CharField(choices=[('SHARING', 'Sharing'), ('SEO', 'SEO')], default='SHARING', max_length=20),
        ),
        migrations.AddField(
            model_name='blogposttitlesuggestion',
            name='suggested_meta_description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='blogposttitlesuggestion',
            name='target_keywords',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
        migrations.AddField(
            model_name='project',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='project',
            name='html_content',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='project',
            name='markdown_content',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='project',
            name='title',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
    ]
