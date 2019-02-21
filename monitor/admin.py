from django.contrib import admin
from . import models

admin.site.register(models.Student)
admin.site.register(models.Course)
admin.site.register(models.DataSets)
admin.site.register(models.MonitorLog)
admin.site.register(models.StudentEncoding)