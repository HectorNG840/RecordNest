from django.shortcuts import render
from django.core.paginator import Paginator
from records.utils import get_oauth_session
from concurrent.futures import ThreadPoolExecutor
import re
from records.deezer_utils import clean_artist_name

def fetch_cover_image(release, session):
    cover_image = release.get("thumb")
    resource_url = release.get("resource_url")
    release_type = release.get("type", "")
    unique_id = release.get("id")

    try:
        if resource_url:
            resp = session.get(resource_url)
            if resp.status_code == 200:
                detail = resp.json()
                images = detail.get("images", [])
                if images:
                    cover_image = images[0].get("uri", cover_image)
            else:
                print(f"Discogs respondió {resp.status_code} para {release.get('title')}")
    except Exception as e:
        print(f"Error con {release.get('title')} : {e}")

    print(f"{release.get('title')} | TYPE: {release_type} | ID: {unique_id}")

    return {
        "title": release.get("title"),
        "type": release_type,
        "year": release.get("year"),
        "cover_image": cover_image,
        "id": unique_id,
        "artist": release.get("artist", "")
    }

def clean_bbcode(text: str) -> str:
    text = re.sub(r'\[/?[biu]\]', '', text)

    text = re.sub(r'\[a=(.*?)\]', r'\1', text)

    text = re.sub(r'\[/?[^\]]+\]', '', text)

    return text

def clean_title(artist_name, title):
    if title.startswith(artist_name):
        return title[len(artist_name) + 3:]
    return title

def artist_detail(request):
    artist_id = request.GET.get("id", "").strip()
    if not artist_id:
        return render(request, 'artists/artist_detail.html', {'error': 'ID de artista no proporcionado'})

    session = get_oauth_session()

    # Obtener detalles del artista
    detail = session.get(f"https://api.discogs.com/artists/{artist_id}").json()
    artist_name = detail.get("name", "")

    # Obtener el perfil del artista
    raw_profile = detail.get("profile", "")
    profile_clean = clean_bbcode(raw_profile)

    mode = request.GET.get("mode", "main")
    current_page = int(request.GET.get("page", 1))

    # Obtener el término de búsqueda
    search_term = request.GET.get("search", "").strip()

    if search_term:
        clean_artist = clean_artist_name(artist_name)
        print(f"artista limpio: {clean_artist}")
        releases_url = "https://api.discogs.com/database/search"
        params = {
            "q": f"{search_term}",
            "page": current_page,
            "per_page": 100,
            "type": "master",
            "artist": clean_artist,
            "release_title": search_term
        }

        raw_response = session.get(releases_url, params=params).json()

        # Depuración: Verificar la respuesta completa de la API
        print(f"Respuesta de la API: {raw_response}")

        all_releases = raw_response.get("results", [])

        # Si no hay resultados de la búsqueda
        if not all_releases:
            print(f"No se encontraron discos con el término de búsqueda: {search_term}")
            return render(request, 'artists/artist_detail.html', {'error': f'No se encontraron discos con el término "{search_term}"'})

        for release in all_releases:
            release['title'] = clean_title(artist_name, release.get('title', ''))
        filtered = all_releases
        hide_mode_buttons = True
    else:

        releases_url = f"https://api.discogs.com/artists/{artist_id}/releases"
        params = {
            "page": current_page,
            "per_page": 100,
            "sort": "year",
            "sort_order": "desc"
        }

        # Realizar la solicitud de discos
        raw_response = session.get(releases_url, params=params).json()

        all_releases = raw_response.get("releases", [])

        if not all_releases:
            print("No se encontraron discos en la búsqueda")
            return render(request, 'artists/artist_detail.html', {'error': 'No se encontraron discos para este artista'})

        # Filtrar los releases según el modo de visualización
        if mode == "appearances":
            filtered = [r for r in all_releases if r.get("role", "unknown").lower() not in ["main", ""]]
        else:
            filtered = [r for r in all_releases if r.get("role", "unknown").lower() == "main"]

        hide_mode_buttons = False

    paginator = Paginator(filtered, 8)
    paginated = paginator.get_page(current_page)

    with ThreadPoolExecutor(max_workers=10) as executor:
        enhanced_releases = list(executor.map(lambda r: fetch_cover_image(r, session), paginated))


    context = {
        "artist": {
            "id": artist_id,
            "name": artist_name,
            "image_url": detail.get("images", [{}])[0].get("uri", ""),
            "profile": profile_clean
        },
        "releases": enhanced_releases,
        "current_page": current_page,
        "total_pages": paginator.num_pages,
        "mode": mode,
        "has_previous": paginated.has_previous(),
        "has_next": paginated.has_next(),
        "previous_page_number": paginated.previous_page_number() if paginated.has_previous() else None,
        "next_page_number": paginated.next_page_number() if paginated.has_next() else None,
        "search": search_term,
        "hide_mode_buttons": hide_mode_buttons
    }

    return render(request, "artists/artist_detail.html", context)






















