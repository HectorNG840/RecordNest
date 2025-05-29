# artists/urls.py
from django.urls import path
from . import views

app_name = 'artists'

urlpatterns = [
    path('', views.artist_detail, name='artist_detail'),
]