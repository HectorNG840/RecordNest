# Generated by Django 5.1.5 on 2025-07-13 10:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_favoriterecord'),
    ]

    operations = [
        migrations.DeleteModel(
            name='FavoriteRecord',
        ),
    ]
