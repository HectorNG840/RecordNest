from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserRecord
from .background_tasks import update_recommendations_async

@receiver(post_save, sender=UserRecord)
def recalculate_recommendations(sender, instance, created, **kwargs):
    if created:  # solo si se añadió un nuevo disco
        update_recommendations_async(instance.user)
