# main/recommendation.py
import discogs_client
from collection.models import UserRecord
from django.conf import settings
from concurrent.futures import ThreadPoolExecutor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from records.views import get_oauth_session
import requests
import time


def get_discogs_client():
    return discogs_client.Client(
        'RecordNest/1.0',
        consumer_key=settings.DISCOGS_CONSUMER_KEY,
        consumer_secret=settings.DISCOGS_CONSUMER_SECRET,
        token=settings.DISCOGS_OAUTH_TOKEN,
        secret=settings.DISCOGS_OAUTH_SECRET
    )



def buscar_discos_en_discogs(disco_usuario, page=1):
    resultados_discogs = []

    try:
        # Obtener los géneros y estilos del disco
        genre_list = disco_usuario.genres.split(",") if disco_usuario.genres else []
        style_list = disco_usuario.styles.split(",") if disco_usuario.styles else []

        # Buscar usando los géneros y estilos del disco
        genre_query = genre_list[0] if genre_list else None
        style_query = style_list[0] if style_list else None
        
        # Realizamos la búsqueda, limitando los resultados a una página
        url = "https://api.discogs.com/database/search"
        params = {
            "genre": genre_query,
            "style": style_query,
            "type": "release",
            "page": page,
            "per_page": 10  # Limitar a 10 resultados por página
        }

        # Realizamos la consulta a la API de Discogs
        response = requests.get(url, params=params)

        # Depuración: Imprimir toda la respuesta de Discogs para entender la estructura
        print(f"Respuesta completa de Discogs: {response.json()}")  # Muestra toda la respuesta para inspección

        data = response.json()

        # Verificamos si la respuesta contiene los resultados
        results = data.get("results", [])
        if not results:
            print("No se encontraron resultados en Discogs.")
            return []

        # Iteramos sobre los resultados de Discogs
        for result in results:
            print(f"Datos del disco recibido: {result}")  # Muestra los datos de cada resultado

            # Accedemos a los resultados con las claves correctas
            title = result.get("title", "Desconocido")
            artists = result.get("artist", "Desconocido")
            genres = result.get("genre", [])
            styles = result.get("style", [])
            
            # Si genres y styles son listas, los convertimos en una cadena separada por comas
            genres = ', '.join(genres) if isinstance(genres, list) else genres
            styles = ', '.join(styles) if isinstance(styles, list) else styles

            # Accedemos a otros atributos de forma segura
            year = result.get("year", "Desconocido")
            master_id = result.get("master_id", "")
            uri = result.get("uri", "")
            thumb = result.get("cover_image", "")

            # Añadir los discos a la lista de resultados
            resultado = {
                "title": title,
                "artists": artists,
                "genres": genres,
                "styles": styles,
                "year": year,
                "master_id": master_id,
                "uri": uri,
                "thumb": thumb
            }
            resultados_discogs.append(resultado)

        return resultados_discogs

    except Exception as e:
        print(f"Error buscando en Discogs: {e}")
        return []



# Función para obtener recomendaciones
def obtener_recomendaciones(usuario):
    # Paso 1: Obtener todos los discos del usuario (y extraer atributos)
    discos_usuario = UserRecord.objects.filter(user=usuario)
    print(f"Discos del usuario: {discos_usuario}")

    # Convertimos los discos de UserRecord en un formato más accesible
    discos_usuario = [
        {
            "title": disco.title,
            "artists": disco.artists,
            "genres": disco.genres,
            "styles": disco.styles,
            "id": disco.id
        }
        for disco in discos_usuario
    ]
    print(f"Discos del usuario extraídos: {discos_usuario}")

    # Paso 2: Preparar set para excluir discos ya en la colección
    discos_existentes = set((d['title'].strip().lower(), d['artists'].strip().lower(), d['id']) for d in discos_usuario)

    # Paso 3: Obtener discos similares desde Discogs
    discos_discogs = []
    for disco_usuario in discos_usuario:
        page = 1
        while True:
            discos_nuevos = buscar_discos_en_discogs(disco_usuario, page=page)
            if not discos_nuevos:
                break
            discos_discogs.extend(discos_nuevos)
            page += 1  # Avanzar a la siguiente página

    # Verificamos cuántos discos encontramos en Discogs
    print(f"Discos de Discogs encontrados: {len(discos_discogs)}")
    
    if not discos_discogs:
        print("No se encontraron discos en Discogs.")
        return []

    # Paso 4: Combinamos discos de la base de datos y Discogs
    todos_discos = discos_usuario + discos_discogs
    print(f"Total de discos combinados: {len(todos_discos)}")

    # Paso 5: Vectorizar todos los discos
    atributos_todos_discos = []
    for disco in todos_discos:
        if isinstance(disco, dict):  # Si el disco es un diccionario (Discogs)
            texto = f"{disco.get('title', '')} {disco.get('artists', '')} {disco.get('genres', '')} {disco.get('styles', '')}"
        else:  # Si el disco es un modelo UserRecord
            texto = f"{disco['title']} {disco['artists']} {disco['genres']} {disco['styles']}"
        
        atributos_todos_discos.append(texto)

    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(atributos_todos_discos)

    # Paso 6: Calcular similitudes entre discos
    similitudes = cosine_similarity(tfidf_matrix)

    # Paso 7: Generar recomendaciones
    recomendaciones = []
    vistos = set()

    num_discos_usuario = len(discos_usuario)

    for i in range(num_discos_usuario):
        similitudes_con_discogs = list(enumerate(similitudes[i][num_discos_usuario:], start=num_discos_usuario))
        similitudes_con_discogs.sort(key=lambda x: x[1], reverse=True)

        # Verificamos las 5 más similares
        for idx, sim in similitudes_con_discogs[:5]:
            candidato = todos_discos[idx]
            if isinstance(candidato, dict):  # Si es de Discogs
                clave = (candidato.get('title', '').strip().lower(), candidato.get('artists', '').strip().lower(), candidato.get('master_id', ''))
            else:  # Si es un modelo UserRecord
                clave = (candidato['title'].strip().lower(), candidato['artists'].strip().lower(), candidato['id'])

            # Excluir discos ya existentes
            if clave not in discos_existentes and clave not in vistos and sim < 1.0:
                recomendaciones.append(candidato)
                vistos.add(clave)

    print(f"Recomendaciones generadas: {len(recomendaciones)}")
    return recomendaciones
