from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.search, name='search'),
    path('record/detail/', views.record_detail, name='record_detail'),
    path('load-versions/<int:master_id>/', views.load_versions, name='load_versions'),

    


]
