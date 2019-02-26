from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import MonitorLog

@receiver(post_save, sender=MonitorLog)
def pass_to_front(sender, **kwargs):
	print(kwargs, "This shit  is working promise this is awesome")
