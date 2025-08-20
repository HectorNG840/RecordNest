from django.urls import path
from . import views

urlpatterns = [
    # Rutas de las estadísticas
    path('most_added/', views.most_added_records, name='most_added_records'),
    path('most_wished/', views.most_wished_records, name='most_wished_records'),
    path('statistics/', views.statistics, name='statistics'),
    path('top_records/', views.top_records, name='top_records'),
]