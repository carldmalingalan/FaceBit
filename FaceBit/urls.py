"""Testing URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
# from django.conf import settings
from FaceBit import settings
from django.contrib import admin
from django.urls import path

import monitor.views as monitor_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', monitor_view.monitor_home, name='monitor-home'),
    path('stream/', monitor_view.monitor_stream, name='monitor-stream'),
    path('profile/image/save/', monitor_view.profile_dataset_save, name='profile-dataset-save'), 
    path('register/', monitor_view.register_student, name='register-student'),
    path('register/<int:pk>/profile/', monitor_view.profile_register, name='register-profile'),
    path('delete/<int:pk>', monitor_view.delete_student, name='delete-student'),
    path('training/', monitor_view.training, name='training'),
    path('training/state/', monitor_view.fetch_state, name='training-state'),
    path('dashboard/', monitor_view.dashboard, name='dashboard'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.DATASETS_URL, document_root=settings.DATASETS_ROOT)