from urllib.parse import unquote
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.core.cache import cache
from .models import Record
import hashlib
import discogs_client
import json

d = discogs_client.Client(
    'RecordNest/0.1',
    user_token='evTZafZyPDstFshQJVwKuGfBhcrbjGgXzYBJdMWl'
)


def search(request):
    query = request.GET.get("q", "").strip()

    try:
        page_number = int(request.GET.get('page', 1))
        if page_number < 1:
            page_number = 1
    except ValueError:
        page_number = 1

    print(f"📄 Página solicitada: {page_number}")

    cache_key = f"search_{hashlib.md5(query.encode()).hexdigest()}_page_{page_number}"
    cached_data = cache.get(cache_key)

    if cached_data:
        print(f"⚡ Cargando desde caché: {cache_key}")
        return render(request, 'records/search.html', cached_data)

    if not query:
        return render(request, 'records/search.html', {
            'error': "Debes ingresar un término de búsqueda",
            'query': query
        })

    try:
        results = d.search(query, type="master", per_page=6, page=page_number)
        total_pages = results.pages
        print(f"📄 Total de páginas disponibles según Discogs: {total_pages}")

        results_page = results.page(page_number)
        processed_results = []

        for record in results_page:
            try:
                main_release = None
                if hasattr(record, 'main_release') and record.main_release:
                    main_release = record.main_release
                    main_release.refresh()

                    print("_________________________________________________")
                    if "tracklist" in main_release.data:
                        print("✅ Tracklist encontrado:")
                        print(json.dumps(main_release.data["tracklist"], indent=4))
                    else:
                        print("❌ Tracklist NO encontrado en main_release.data")

                first_image_url = None
                if main_release and hasattr(main_release, 'images') and main_release.images:
                    first_image_url = main_release.images[0]['uri']
                
                artists = ', '.join(
                    artist.name for artist in getattr(main_release, 'artists', [])
                ) if main_release and hasattr(main_release, 'artists') else "Desconocido"

                processed_results.append({
                    'image_url': first_image_url,
                    'title': main_release.title if main_release else record.title,
                    'artists': artists,
                    'year': main_release.year if main_release else record.year,
                    'avg_rating': main_release.data.get("community", {}).get("rating", {}).get("average", "N/A") if main_release else "N/A",
                    'released': main_release.data.get("released", 'Desconocido') if main_release else 'Desconocido',
                    'notes': main_release.notes if main_release and hasattr(main_release, 'notes') else 'No notes available',
                    'barcode': ', '.join(main_release.barcode) if main_release and hasattr(main_release, 'barcode') else 'No barcode available',
                    'tags': ', '.join(main_release.tags) if main_release and hasattr(main_release, 'tags') else 'No tags',
                    'genres': ', '.join(main_release.genres) if main_release and hasattr(main_release, 'genres') else "Desconocido",
                    'styles': ', '.join(main_release.styles) if main_release and hasattr(main_release, 'styles') else "Desconocido",
                    'labels': ', '.join(label.name for label in getattr(main_release, 'labels', [])) if main_release and hasattr(main_release, 'labels') else "Desconocido",
                    'formats': ', '.join(fmt['name'] for fmt in getattr(main_release, 'formats', [])) if main_release and hasattr(main_release, 'formats') else "Desconocido",
                    'tracklist': json.dumps([
                        {
                            'position': track.get("position", "N/A"),
                            'title': track.get("title", "Unknown Title"),
                            'duration': track.get("duration", "N/A")
                        } for track in main_release.data.get("tracklist", [])
                    ], ensure_ascii=False) if main_release else "[]"

                })
            except Exception as e:
                print(f"⚠️ Error al procesar un resultado ({record.title}): {type(e).__name__} - {e}")

        print(f"✅ Total de resultados en la página {page_number}: {len(processed_results)}")

        paginator = Paginator(processed_results, 6)
        page_obj = paginator.get_page(page_number)

        print(f"🔍 Parámetros GET: {request.GET}")

        cached_data = {
            'query': query,
            'page_obj': page_obj,
            'total_pages': total_pages,
            'current_page': page_number
        }
        cache.set(cache_key, cached_data, timeout=600)

        return render(request, 'records/search.html', cached_data)

    except Exception as e:
        print(f"❌ Error general en la búsqueda: {type(e).__name__} - {e}")
        return render(request, 'records/search.html', {
            'error': f"Error en la búsqueda: {str(e)}",
            'query': query
        })


def record_detail(request):
    title = request.GET.get('title', 'Unknown Title')
    artists = request.GET.get('artists', 'Unknown Artist')
    image_url = request.GET.get('image_url', '')
    year = request.GET.get('year', 'Unknown Year')
    avg_rating = request.GET.get('avg_rating', 'N/A')
    released = request.GET.get('released', 'Desconocido')
    notes = request.GET.get('notes', 'No notes available')
    barcode = request.GET.get('barcode', 'No barcode available')
    tags = request.GET.get('tags', 'No tags')
    genres = request.GET.get('genres', 'Unknown Genre')
    styles = request.GET.get('styles', 'Unknown Style')
    labels = request.GET.get('labels', 'Unknown Label')
    formats = request.GET.get('formats', 'Unknown Format')

    tracklist_json = request.GET.get('tracklist', '[]')

    print(f"📥 Tracklist recibido en la URL: {tracklist_json}")

    try:
        decoded_tracklist = unquote(tracklist_json)  # Decodifica caracteres especiales
        print(f"✅ Tracklist decodificado de la URL: {decoded_tracklist}")  # Verificar antes de cargar JSON
        tracklist = json.loads(decoded_tracklist)  # Intenta decodificar JSON
    except json.JSONDecodeError as e:
        print(f"❌ Error al decodificar tracklist: {e}")
        tracklist = []

    record = {
        'title': title,
        'artists': artists,
        'image_url': image_url,
        'year': year,
        'avg_rating': avg_rating,
        'released': released,
        'notes': notes,
        'barcode': barcode,
        'tags': tags,
        'genres': genres,
        'styles': styles,
        'labels': labels,
        'formats': formats,
        'tracklist': tracklist
    }

    return render(request, 'records/record_detail.html', {'record': record})
