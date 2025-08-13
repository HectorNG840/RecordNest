from django.shortcuts import render
from .recomendation import obtener_recomendaciones

# Create your views here.
def index(request):
    return render(request, 'main/base.html')

def home(request):
    return render(request, 'main/home.html')

def recomendaciones_view(request):
    usuario = request.user  # Obtener el usuario actual
    recomendaciones = obtener_recomendaciones(usuario)
    
    print(f"Recomendaciones: {recomendaciones}")
    
    return render(request, 'main/recomendaciones.html', {'recomendaciones': recomendaciones})