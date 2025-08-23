from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="users/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="index"), name="logout"),
    path("profile/<str:username>/", views.profile, name="profile"),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('edit/', views.edit_profile, name='edit_profile'),
    path('delete_profile/', views.delete_profile, name='delete_profile'),
    path('favorites/select/<int:slot>/', views.select_favorite_record, name='select_favorite_record'),
    path('search/', views.user_search, name='user_search'),


]
