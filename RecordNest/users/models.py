from django.db import models
from django.contrib.auth.hashers import make_password, is_password_usable
from django.contrib.auth.models import AbstractUser

# Create your models here.


class CustomUser(AbstractUser):
    name = models.CharField(max_length=250)
    birthday = models.DateField(null=True, blank=True)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=False)

    profile_image = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.png')
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.username
