from urllib.parse import unquote
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.core.cache import cache
from .models import Record
import hashlib
import discogs_client
import json
from django.conf import settings
from .deezer_utils import get_preview_url_from_deezer, get_deezer_results, normalize_name, fetch_deezer_info
from django.http import HttpResponse
from django.http import JsonResponse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests_oauthlib import OAuth1Session
from django.conf import settings
from math import ceil
import time
import requests
from discogs_client.exceptions import HTTPError


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
            "id": artist_id,
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



def fetch_preview_url(request, track_id):
    try:
        response = requests.get(f"https://api.deezer.com/track/{track_id}")
        data = response.json()
        return JsonResponse({'preview': data.get("preview")})
    except Exception as e:
        return JsonResponse({'preview': None, 'error': str(e)}, status=500)


def track_position_key(pos):
    match = re.match(r"([A-Z])(\d+)", pos.upper())
    if match:
        letter, number = match.groups()
        return (ord(letter), int(number))
    return (float('inf'), float('inf'))

def record_detail(request):
    master_id = request.GET.get("master_id")
    release_id = request.GET.get("release_id")
    title = request.GET.get('title', '').strip()
    artists_param = request.GET.get('artists', '').strip()

    clean_artist = re.sub(r'\s*\(\d+\)$', '', artists_param) if artists_param else None
    session = get_oauth_session()

    try:
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

        # Fallbacks
        if not clean_artist:
            artist_data = release.get("artists", [])
            clean_artist = re.sub(r"\s*\(\d+\)$", "", artist_data[0].get("name", "").strip()) if artist_data else "Unknown Artist"
        if not title:
            title = release.get("title", "").strip()

        images = [img['uri'] for img in release.get('images', []) if img.get('uri')]

        # Tracklist
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

                    if duration_secs and deezer_duration:
                        if abs(deezer_duration - duration_secs) <= 2 and normalize_name(deezer_artist) == normalize_name(clean_artist):
                            deezer_info = {
                                "preview_url": res["preview"],
                                "deezer_link": res["link"],
                                "deezer_artists": [deezer_artist],
                                "deezer_id": res["id"]
                            }
                            break
                    elif not duration_secs and res.get("preview"):
                        if normalize_name(clean_artist) in normalize_name(deezer_artist):
                            deezer_info = {
                                "preview_url": res["preview"],
                                "deezer_link": res["link"],
                                "deezer_artists": [deezer_artist],
                                "deezer_id": res["id"]
                            }
                            break

            tracklist.append({
                "position": track.get("position", ""),
                "title": track_title,
                "duration": duration,
                "preview_url": deezer_info.get("preview_url") if deezer_info else None,
                "deezer_link": deezer_info.get("deezer_link") if deezer_info else None,
                "deezer_artists": deezer_info.get("deezer_artists") if deezer_info else [],
                "id": deezer_info.get("deezer_id") if deezer_info else None
            })

        tracklist.sort(key=lambda track: track_position_key(track.get("position", "")))

        record = {
            'title': release.get("title", "Sin título"),
            'artists': ', '.join(a['name'] for a in release.get("artists", [])) or "Desconocido",
            'images': images,
            'year': release.get("year", "Desconocido"),
            'avg_rating': release.get("community", {}).get("rating", {}).get("average", "N/A"),
            'released': release.get("released", "Desconocido"),
            'notes': release.get("notes", "No hay notas"),
            'barcode': ', '.join(i['value'] for i in release.get('identifiers', []) if i.get('type') == 'Barcode') or 'No disponible',
            'tags': "",
            'genres': ', '.join(release.get('genres', [])) or 'Desconocido',
            'styles': ', '.join(release.get('styles', [])) or 'Desconocido',
            'labels': ', '.join(label.get('name') for label in release.get('labels', [])) or 'Desconocido',
            'formats': ', '.join(fmt.get('name') for fmt in release.get('formats', [])) or 'Desconocido',
            'tracklist': tracklist,
            'versions': [],
            'master_id': master_id or release.get("master_id")
        }

        return render(request, 'records/record_detail.html', {'record': record})

    except Exception as e:
        print(f"❌ Error en record_detail: {e}")
        return render(request, 'records/record_detail.html', {'record': {}, 'error': str(e)})



def extract_version_data(rel):
    data = rel.data
    identifiers = data.get('identifiers', [])

    barcodes = [i['value'].strip() for i in identifiers
                if i.get('type', '').lower() == 'barcode' and i.get('value')]

    if barcodes:
        return {
            'id': rel.id,
            'year': data.get('year') or 'Desconocido',
            'country': data.get('country') or 'Desconocido',
            'format': ', '.join(fmt['name'] for fmt in data.get('formats', [])) or '',
            'label': ', '.join(label['name'] for label in data.get('labels', [])) or '',
            'barcode': ', '.join(barcodes),
            'barcode_type': 'Barcode'
        }

    fallback = [f"{i.get('type')}: {i.get('value')}" for i in identifiers if i.get('value')]
    return {
        'id': rel.id,
        'year': data.get('year') or 'Desconocido',
        'country': data.get('country') or 'Desconocido',
        'format': ', '.join(fmt['name'] for fmt in data.get('formats', [])) or '',
        'label': ', '.join(label['name'] for label in data.get('labels', [])) or '',
        'barcode': '; '.join(fallback[:5]) + ('...' if len(fallback) > 5 else ''),
        'barcode_type': 'Identificadores'
    }


def fetch_version(discogs_client, version_obj):
    try:
        rel = discogs_client.release(version_obj.id)
        rel.refresh()
        return extract_version_data(rel)
    except HTTPError as e:
        print(f"❌ Error al procesar release {version_obj.id}: {e}")
        return None


def load_versions(request):
    master_id = request.GET.get("master_id")
    offset = int(request.GET.get("offset", 0))
    limit = int(request.GET.get("limit", 10))

    try:
        d = get_discogs_client()
        master = d.master(master_id)
        all_versions = list(master.versions)
        batch = all_versions[offset:offset + limit]

        versions = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_version, d, v) for v in batch]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    versions.append(result)

        def parse_year(y):
            try:
                return int(y)
            except Exception:
                return 9999

        versions.sort(key=lambda v: (parse_year(v['year']), v['country']))

        return JsonResponse({'versions': versions})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    




