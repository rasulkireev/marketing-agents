# Generated by Django 5.1.6 on 2025-03-11 08:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_pricingpageupdatessuggestion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectpage',
            name='type',
            field=models.CharField(blank=True, choices=[('Blog', 'Blog'), ('About', 'About'), ('Contact', 'Contact'), ('FAQ', 'FAQ'), ('Terms of Service', 'Terms of Service'), ('Privacy Policy', 'Privacy Policy'), ('Pricing', 'Pricing'), ('Other', 'Other')], max_length=255, null=True),
        ),
    ]
