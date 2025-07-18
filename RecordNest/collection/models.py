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

class FavoriteRecord(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="favorite_record")
    record_1 = models.ForeignKey(UserRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    record_2 = models.ForeignKey(UserRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    record_3 = models.ForeignKey(UserRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    def __str__(self):
        return f"Favoritos de {self.user.username}"


class Track(models.Model):
    record = models.ForeignKey(UserRecord, on_delete=models.CASCADE, related_name="tracks")
    position = models.CharField(max_length=10, blank=True)
    title = models.CharField(max_length=255)
    duration = models.CharField(max_length=20, blank=True)
    preview_url = models.URLField(blank=True)
    deezer_link = models.URLField(blank=True)
    deezer_artists = models.TextField(blank=True)
    deezer_id = models.CharField(max_length=50, blank=True, null=True) 

    def __str__(self):
        return f"{self.position} - {self.title}"

class RecordList(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cover_image = models.ImageField(upload_to='list_covers/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    records = models.ManyToManyField("UserRecord", related_name="lists")
    is_public = models.BooleanField(default=False)

    def __str__(self):
        return self.name

