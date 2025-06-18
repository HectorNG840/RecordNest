from django.db import models
from users.models import CustomUser as User

class Tag(models.Model):
    name = models.CharField(max_length=50)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tags")

    class Meta:
        unique_together = ("name", "user")

    def __str__(self):
        return self.name
    
class UserRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    artists = models.CharField(max_length=255)
    year = models.CharField(max_length=10, blank=True)
    cover_image = models.URLField(blank=True)
    released = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    barcode = models.CharField(max_length=100, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="records")
    genres = models.TextField(blank=True)
    styles = models.TextField(blank=True)
    labels = models.TextField(blank=True)
    formats = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    tracklist_JSON = models.JSONField(default=list, blank=True)


class Track(models.Model):
    record = models.ForeignKey(UserRecord, on_delete=models.CASCADE, related_name="tracks")
    position = models.CharField(max_length=10, blank=True)
    title = models.CharField(max_length=255)
    duration = models.CharField(max_length=20, blank=True)
    preview_url = models.URLField(blank=True)
    deezer_link = models.URLField(blank=True)
    deezer_artists = models.TextField(blank=True)

    def __str__(self):
        return f"{self.position} - {self.title}"

class RecordList(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)
    records = models.ManyToManyField("UserRecord", related_name="lists")

    def __str__(self):
        return self.name

