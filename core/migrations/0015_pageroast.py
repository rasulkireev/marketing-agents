# Generated by Django 5.1.7 on 2025-03-12 14:32

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_alter_projectpage_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='PageRoast',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('roaster', models.CharField(choices=[('Sam Parr', 'Sam Parr'), ('Alex Hormozi', 'Alex Hormozi')], default='Sam Parr', max_length=255)),
                ('url', models.URLField()),
                ('date_scraped', models.DateTimeField(blank=True, null=True)),
                ('title', models.CharField(blank=True, default='', max_length=500)),
                ('description', models.TextField(blank=True, default='')),
                ('html_content', models.TextField(blank=True, default='')),
                ('markdown_content', models.TextField(blank=True, default='')),
                ('roasting_content', models.TextField(blank=True, default='')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
