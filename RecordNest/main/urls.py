from django.urls import include, path
from . import views
from records import views as record_views
from django.views.generic import TemplateView

urlpatterns = [
    path('', views.home, name='index'),
    path('search/', include('records.urls')),
    path('sobre-nosotros/', TemplateView.as_view(template_name="main/about.html"), name="about"),
    path('load-versions/<int:master_id>/', record_views.load_versions, name='load_versions'),
    path('recomendaciones/', views.recomendaciones_view, name='recomendaciones'),
]
