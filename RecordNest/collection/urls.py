from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
path("add/", views.add_to_collection, name="add_to_collection"),
path("mi-coleccion/", views.my_collection, name="my_collection"),
path("mi-coleccion/<int:pk>/", views.local_record_detail, name="local_record_detail"),
path('record/<int:record_id>/', views.local_record_detail, name='local_record_detail'),
path("delete/<int:record_id>/", views.delete_from_collection, name="delete_from_collection"),
path("collection/record/<int:record_id>/add_tag/", views.add_tag, name="add_tag"),
path("collection/<int:record_id>/remove-tag/<int:tag_id>/", views.remove_tag, name="remove_tag"),


]