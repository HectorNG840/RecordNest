from django.urls import include, path
from . import views
from records import views as record_views

urlpatterns = [
    path('', views.home, name='index'),
    path('search/', include('records.urls')),
    path('load-versions/<int:master_id>/', record_views.load_versions, name='load_versions'),
]
