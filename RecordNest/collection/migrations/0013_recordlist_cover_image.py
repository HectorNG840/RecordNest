# Generated by Django 5.1.5 on 2025-07-14 09:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0012_favoriterecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='recordlist',
            name='cover_image',
            field=models.ImageField(blank=True, null=True, upload_to='record_lists/'),
        ),
    ]
