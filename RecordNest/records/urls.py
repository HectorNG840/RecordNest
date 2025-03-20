from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.search, name='search'),
    path('record/detail/', views.record_detail, name='record_detail'),
]
