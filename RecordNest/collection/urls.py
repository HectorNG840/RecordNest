from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
path("/add/", views.add_to_collection, name="add_to_collection"),
path("mi-coleccion/", views.my_collection, name="my_collection"),
path("mi-coleccion/<int:pk>/", views.local_record_detail, name="local_record_detail"),
]