from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.search, name='search'),
    path('record/detail/', views.record_detail, name='record_detail'),
    path("ajax/load_versions/", views.load_versions, name="load_versions"),
    path("ajax/preview/<int:track_id>/", views.fetch_preview_url, name="fetch_preview"),


    


]
