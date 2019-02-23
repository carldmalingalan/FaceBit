import os
from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FaceBit.settings")

app = Celery('FaceBit', backend="rpc://")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()