from django.db import models
from django.contrib.auth.hashers import make_password

# Create your models here.


class User(models.Model):
    username = models.CharField(max_length=250)
    name = models.CharField(max_length=250)
    password = models.CharField(max_length=250)
    birthday = models.DateField()
    email = models.EmailField()

    def save(self, *args, **kwargs):
        self.password = make_password(self.password)
        super(User, self).save(*args, **kwargs)

    def __str__(self):
        return self.username
