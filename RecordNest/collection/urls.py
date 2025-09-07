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
path('tags/delete/<int:tag_id>/', views.delete_tag, name='delete_tag'),
path("collection/tags/add/", views.add_tag_to_collection, name="add_tag_to_collection"),
path("lists/", views.my_lists, name="my_lists"),
path("lists/create/", views.create_list, name="create_list"),
path('record/<int:record_id>/add_to_list/<int:list_id>/', views.add_record_to_list, name='add_record_to_list'),
path('lists/<int:list_id>/delete/', views.delete_list, name='delete_list'),
path('lists/<int:list_id>/edit/', views.edit_list, name='edit_list'),
path('lists/<int:list_id>/', views.list_detail, name='list_detail'),
path('lists/<int:list_id>/remove/<int:record_id>/', views.remove_record_from_list, name='remove_record_from_list'),
path("ajax/preview/<int:track_id>/", views.fetch_preview_url, name="fetch_preview_url"),
path('add_to_wishlist/<str:discogs_id>/', views.add_to_wishlist, name='add_to_wishlist'),
path('remove_from_wishlist/<int:wishlist_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
path('wishlist/', views.user_wishlist, name='user_wishlist'),
path("recommendations/", views.recommendations_page, name="recommendations_page"),
path("recommendations/exclude/<str:master_id>/", views.exclude_recommendation, name="exclude_recommendation"),
path("api/recommendations/", views.recommendations_api, name="recommendations_api"),






]