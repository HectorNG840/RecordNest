from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings




class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico es obligatorio.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if not extra_fields.get('is_staff'):
            raise ValueError('Superuser debe tener is_staff=True.')
        if not extra_fields.get('is_superuser'):
            raise ValueError('Superuser debe tener is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = models.CharField(max_length=150, unique=True, blank=True)
    name = models.CharField(max_length=250)
    birthday = models.DateField(null=True, blank=True)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)

    profile_image = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.png')
    bio = models.TextField(blank=True, null=True)

    objects = CustomUserManager()

    def __str__(self):
        return self.email
