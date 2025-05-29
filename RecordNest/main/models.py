from django.db import models

from django.conf import settings




class Collection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lenght = models.IntegerField()
    creation_date = models.DateField()
    records = models.ManyToManyField('records.Record',
                                     related_name='collections')

    def __str__(self):
        return self.lenght
