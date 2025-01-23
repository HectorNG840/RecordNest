from django.db import models

# Create your models here.
class Record(models.Model):
    year = models.IntegerField()
    avg_rating = models.FloatField()
    title = models.CharField(max_length=250)
    released = models.IntegerField()
    notes = models.CharField(max_length=500)
    barcode = models.IntegerField()
    date_added = models.DateField()
    tags = models.CharField(max_length=250)

    def __str__(self):
        return self.title
    
    @property
    def images(self):
        return self.images.all()
    
    @property
    def tracks(self):
        return self.tracks.all()

class Image(models.Model):
    record = models.ForeignKey(Record, related_name='images')
    type = models.CharField(max_length=100)
    image = models.ImageField(upload_to='record_images/')

class Track(models.Model):
    record = models.ForeignKey(Record, related_name='tracks')
    position = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    duration = models.DurationField()

class Artist(models.Model):
    name = models.CharField(max_length=150)
    thumbnail = models.ImageField(upload_to='artist_images/')
    records = models.ManyToManyField(Record, related_name='artists')

    def __str__(self):
        return self.name
    
class Label(models.Model):
    name = models.CharField(max_length=150)
    thumbnail = models.ImageField(upload_to='label_images/')
    records = models.ManyToManyField(Record, related_name='labels')

    def __str__(self):
        return self.name

class Format(models.Model):
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=250)
    text = models.CharField(max_length=250)
    records = models.ManyToManyField(Record, related_name='labels')

    def __str__(self):
        return self.name

class Genre(models.Model):
    name = models.CharField(max_length=150)
    records = models.ManyToManyField(Record, related_name='labels')

    def __str__(self):
        return self.name

class Style(models.Model):
    name = models.CharField(max_length=150)
    records = models.ManyToManyField(Record, related_name='labels')

    def __str__(self):
        return self.name


