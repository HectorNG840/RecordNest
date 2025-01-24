# Generated by Django 5.1.5 on 2025-01-24 10:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Record',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.IntegerField()),
                ('avg_rating', models.FloatField()),
                ('title', models.CharField(max_length=250)),
                ('released', models.IntegerField()),
                ('notes', models.CharField(max_length=500)),
                ('barcode', models.IntegerField()),
                ('date_added', models.DateField()),
                ('tags', models.CharField(max_length=250)),
            ],
        ),
        migrations.CreateModel(
            name='Label',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('thumbnail', models.ImageField(upload_to='label_images/')),
                ('records', models.ManyToManyField(related_name='labels', to='records.record')),
            ],
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(max_length=100)),
                ('image', models.ImageField(upload_to='record_images/')),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='records.record')),
            ],
        ),
        migrations.CreateModel(
            name='Genre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('records', models.ManyToManyField(related_name='genres', to='records.record')),
            ],
        ),
        migrations.CreateModel(
            name='Format',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('description', models.CharField(max_length=250)),
                ('text', models.CharField(max_length=250)),
                ('records', models.ManyToManyField(related_name='formats', to='records.record')),
            ],
        ),
        migrations.CreateModel(
            name='Artist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('thumbnail', models.ImageField(upload_to='artist_images/')),
                ('records', models.ManyToManyField(related_name='artists', to='records.record')),
            ],
        ),
        migrations.CreateModel(
            name='Style',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('records', models.ManyToManyField(related_name='styles', to='records.record')),
            ],
        ),
        migrations.CreateModel(
            name='Track',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.CharField(max_length=100)),
                ('title', models.CharField(max_length=100)),
                ('duration', models.DurationField()),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tracks', to='records.record')),
            ],
        ),
    ]
