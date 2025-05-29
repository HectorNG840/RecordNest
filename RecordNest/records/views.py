from urllib.parse import unquote
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.core.cache import cache
from .models import Record
import hashlib
import discogs_client
import json
from django.conf import settings
from .deezer_utils import get_preview_url_from_deezer, get_deezer_results, normalize_name
from django.http import HttpResponse
from django.http import JsonResponse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests_oauthlib import OAuth1Session
from django.conf import settings
from math import ceil
import time


def get_oauth_session():
    return OAuth1Session(
        settings.DISCOGS_CONSUMER_KEY,
        client_secret=settings.DISCOGS_CONSUMER_SECRET,
        resource_owner_key=settings.DISCOGS_OAUTH_TOKEN,
        resource_owner_secret=settings.DISCOGS_OAUTH_SECRET
    )


def get_discogs_client():
    return discogs_client.Client(
        'RecordNest/1.0',
        consumer_key=settings.DISCOGS_CONSUMER_KEY,
        consumer_secret=settings.DISCOGS_CONSUMER_SECRET,
        token=settings.DISCOGS_OAUTH_TOKEN,
        secret=settings.DISCOGS_OAUTH_SECRET
    )

def search_discogs(query, page=1):
    session = get_oauth_session()
    url = f"https://api.discogs.com/database/search"
    params = {
        "q": query,
        "page": page,
        "per_page": 6
    }
    response = session.get(url, params=params)
    return response.json()

def fetch_artist_detail(result):
    artist_id = result.get("id")
    name = result.get("title", "Desconocido")
    image_url = result.get("thumb")

    try:
        session = get_oauth_session()
        detail_url = f"https://api.discogs.com/artists/{artist_id}"
        detail = session.get(detail_url).json()
        images = detail.get("images", [])
        if images:
            image_url = images[0].get("uri", image_url)
    except:
        pass

    return {
            "type": "artist",
            "name": name,
            "image_url": image_url,
        }
    
def search(request):
    query = request.GET.get("q", "").strip()
    search_type = request.GET.get("type", "master")
    page_number = int(request.GET.get("page", 1) or 1)
    per_page = 8

    if not query:
        return render(request, 'records/search.html', {
            'error': "Debes ingresar un término de búsqueda",
            'query': query
        })

    try:
        session = get_oauth_session()
        url = "https://api.discogs.com/database/search"
        params = {
            "q": query,
            "type": search_type,
            "page": page_number,
            "per_page": per_page
        }

        response = session.get(url, params=params)
        data = response.json()
        results = data.get("results", [])
        total_pages = data.get("pagination", {}).get("pages", 1)
        if not results and total_pages > 1:
            time.sleep(0.6)  # darle tiempo al servidor
            response = session.get(url, params=params)
            data = response.json()
            results = data.get("results", [])

        artist_results = [r for r in results if r.get("type") == "artist"]
        master_results = [r for r in results if r.get("type") == "master"]
        processed_results = []



        with ThreadPoolExecutor(max_workers=5) as executor:
            artist_items = list(executor.map(fetch_artist_detail, artist_results[:8]))

        processed_results.extend(artist_items)

        # MASTERS
        for result in master_results:
            title = result.get("title", "Desconocido")
            if " - " in title:
                artist_name, record_title = title.split(" - ", 1)
            else:
                artist_name, record_title = "Desconocido", title

            processed_results.append({
                "type": "master",
                "image_url": result.get("cover_image"),
                "title": record_title.strip(),
                "year": result.get("year", "Desconocido"),
                "genres": ', '.join(result.get("genre", [])),
                "styles": ', '.join(result.get("style", [])),
                "labels": ', '.join(result.get("label", [])),
                "formats": ', '.join(result.get("format", [])),
                "master_id": result.get("master_id"),
                "artists": artist_name.strip(),
            })

        context = {
            'query': query,
            'type': search_type,
            'results': processed_results,
            'total_pages': total_pages,
            'current_page': page_number
        }

        return render(request, 'records/search.html', context)

    except Exception as e:
        print(f"❌ Error global en search: {e}")
        return render(request, 'records/search.html', {
            'error': f"Error en la búsqueda: {str(e)}",
            'query': query
        })





def record_detail(request):
    master_id = request.GET.get("master_id")
    release_id = request.GET.get("release_id")
    title = request.GET.get('title', '').strip()
    artists_param = request.GET.get('artists', '').strip()

    clean_artist = re.sub(r'\s*\(\d+\)$', '', artists_param) if artists_param else None
    session = get_oauth_session()

    try:
        # Obtener release desde master_id o release_id
        if master_id:
            d = get_discogs_client()
            master = d.master(master_id)
            master.refresh()
            release = master.main_release
            release.refresh()
            release = release.data
        elif release_id:
            release_url = f"https://api.discogs.com/releases/{release_id}"
            release = session.get(release_url).json()
        else:
            query = f"{clean_artist} {title}"
            d = get_discogs_client()
            results = d.search(query, type="master")
            if not results:
                raise ValueError("No se encontró el disco en Discogs.")
            master = next(
                (r for r in results if clean_artist and clean_artist.lower() in r.title.lower() and title.lower() in r.title.lower()),
                results[0]
            )
            master.refresh()
            release = master.main_release
            release.refresh()
            release = release.data

        # Fallbacks para artista y título si vienen vacíos
        if not clean_artist:
            artist_data = release.get("artists", [])
            if artist_data and isinstance(artist_data, list):
                clean_artist = re.sub(r"\s*\(\d+\)$", "", artist_data[0].get("name", "").strip())
            else:
                clean_artist = "Unknown Artist"

        if not title:
            title = release.get("title", "").strip()

        # Reconstruir query de búsqueda
        query = f"{clean_artist} {title}"

        # Imágenes del álbum
        images = [img['uri'] for img in release.get('images', []) if img.get('uri')]

        # Tracklist con previews de Deezer
        tracklist = []
        for track in release.get("tracklist", []):
            track_title = track.get("title", "Unknown")
            duration = track.get("duration", "N/A")
            deezer_info = None
            duration_secs = None

            if duration and ":" in duration:
                try:
                    minutes, seconds = map(int, duration.split(":"))
                    duration_secs = minutes * 60 + seconds
                except ValueError:
                    pass

            deezer_results = get_deezer_results(track_title, clean_artist or "")
            if deezer_results:
                for res in deezer_results:
                    deezer_duration = res.get("duration")
                    deezer_artist = res["artist"]["name"]

                    # Match estricto por duración
                    if duration_secs and deezer_duration:
                        if abs(deezer_duration - duration_secs) <= 2 and normalize_name(deezer_artist) == normalize_name(clean_artist):
                            deezer_info = {
                                "preview_url": res["preview"],
                                "deezer_link": res["link"],
                                "deezer_artists": [deezer_artist]
                            }
                            break

                    # Match sin duración, pero con preview disponible y coincidencia de nombre
                    elif not duration_secs and res.get("preview"):
                        if normalize_name(clean_artist) in normalize_name(deezer_artist):
                            deezer_info = {
                                "preview_url": res["preview"],
                                "deezer_link": res["link"],
                                "deezer_artists": [deezer_artist]
                            }
                            break

            tracklist.append({
                "position": track.get("position", ""),
                "title": track_title,
                "duration": duration,
                "preview_url": deezer_info.get("preview_url") if deezer_info else None,
                "deezer_link": deezer_info.get("deezer_link") if deezer_info else None,
                "deezer_artists": deezer_info.get("deezer_artists") if deezer_info else []
            })

        # Construcción del contexto final del disco
        record = {
            'title': release.get("title", "Sin título"),
            'artists': ', '.join(a['name'] for a in release.get("artists", [])) or "Desconocido",
            'images': images,
            'year': release.get("year", "Desconocido"),
            'avg_rating': release.get("community", {}).get("rating", {}).get("average", "N/A"),
            'released': release.get("released", "Desconocido"),
            'notes': release.get("notes", "No hay notas"),
            'barcode': ', '.join(i['value'] for i in release.get('identifiers', []) if i.get('type') == 'Barcode') or 'No disponible',
            'tags': 'Sin etiquetas',
            'genres': ', '.join(release.get('genres', [])) or 'Desconocido',
            'styles': ', '.join(release.get('styles', [])) or 'Desconocido',
            'labels': ', '.join(label.get('name') for label in release.get('labels', [])) or 'Desconocido',
            'formats': ', '.join(fmt.get('name') for fmt in release.get('formats', [])) or 'Desconocido',
            'tracklist': tracklist,
            'versions': [],  # Para ser cargado vía AJAX si se desea
            'master_id': master_id or release.get("master_id")
        }

        return render(request, 'records/record_detail.html', {'record': record})

    except Exception as e:
        print(f"❌ Error en record_detail: {e}")
        return render(request, 'records/record_detail.html', {'record': {}, 'error': str(e)})





def load_versions(request, master_id):
    d = get_discogs_client()
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 4))

    try:
        master = d.master(master_id)
        all_versions = list(master.versions)

        start = (page - 1) * per_page
        end = start + per_page
        versions_page = all_versions[start:end]

        version_list = []
        for v in versions_page:
            rel = d.release(v.id)
            rel.refresh()
            rel_data = rel.data

            version_list.append({
                'id': rel.id,
                'year': rel_data.get('year') or 'Desconocido',
                'country': rel_data.get('country') or 'Desconocido',
                'format': ', '.join(fmt['name'] for fmt in rel_data.get('formats', [])),
                'label': ', '.join(label['name'] for label in rel_data.get('labels', [])),
                'barcode': ', '.join(i['value'] for i in rel_data.get('identifiers', []) if i.get('type') == 'Barcode') or "No disponible"
            })

        return JsonResponse({'versions': version_list,
                             'has_more': len(versions_page) == per_page
                             })

    except Exception as e:
        print(f"⚠️ Error en load_versions: {e}")
        return JsonResponse({'versions': []})



def fetch_release_data(record):
    main_release = getattr(record, 'main_release', None)
    if not main_release:
        return None

    cache_key = f"release_{main_release.id}"
    main_data = cache.get(cache_key)
    if main_data:
        return (record, main_data)

    try:
        main_release.refresh()
        main_data = main_release.data
        cache.set(cache_key, main_data, timeout=3600)
        return (record, main_data)
    except Exception as e:
        print(f"⚠️ Error al refrescar {record.title}: {e}")
        return None
    




