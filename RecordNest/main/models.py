from django.db import models

# Create your models here.


class Collection(models.Model):
    user = models.OneToOneField('users.User', on_delete=models.CASCADE,
                                related_name='collection')
    lenght = models.IntegerField()
    creation_date = models.DateField()
    records = models.ManyToManyField('records.Record',
                                     related_name='collections')

    def __str__(self):
        return self.lenght
