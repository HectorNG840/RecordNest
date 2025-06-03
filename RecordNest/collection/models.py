from django.db import models
from users.models import CustomUser as User

class UserRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    artists = models.CharField(max_length=255)
    year = models.CharField(max_length=10, blank=True)
    cover_image = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
