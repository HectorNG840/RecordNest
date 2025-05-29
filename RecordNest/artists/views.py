from django.shortcuts import render
from django.core.paginator import Paginator
from records.views import get_oauth_session
from concurrent.futures import ThreadPoolExecutor

def fetch_cover_image(release, session):
    cover_image = release.get("thumb")  # fallback por defecto
    resource_url = release.get("resource_url")
    release_type = release.get("type", "")  # master o release
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
                print(f"⚠️ Discogs respondió {resp.status_code} para {release.get('title')}")
    except Exception as e:
        print(f"⚠️ Error con {release.get('title')} : {e}")

    print(f"🔍 {release.get('title')} | TYPE: {release_type} | ID: {unique_id}")

    return {
        "title": release.get("title"),
        "type": release_type,
        "year": release.get("year"),
        "cover_image": cover_image,
        "id": unique_id,
        "artist": release.get("artist", "")
    }


def artist_detail(request):
    artist_name = request.GET.get("name", "").strip()
    if not artist_name:
        return render(request, 'artists/artist_detail.html', {'error': 'Nombre de artista no proporcionado'})

    session = get_oauth_session()
    search_url = "https://api.discogs.com/database/search"
    params = {"q": artist_name, "type": "artist", "per_page": 1, "page": 1}

    response = session.get(search_url, params=params)
    data = response.json()
    result = data.get("results", [])[0] if data.get("results") else None

    if not result:
        return render(request, 'artists/artist_detail.html', {'error': 'Artista no encontrado'})

    artist_id = result["id"]
    detail = session.get(f"https://api.discogs.com/artists/{artist_id}").json()

    mode = request.GET.get("mode", "main")
    current_page = int(request.GET.get("page", 1))

    # Obtener releases (1 página = 100 items max)
    releases_url = f"https://api.discogs.com/artists/{artist_id}/releases"
    raw_response = session.get(releases_url, params={"page": 1, "per_page": 100}).json()
    all_releases = raw_response.get("releases", [])

    if mode == "appearances":
        filtered = [r for r in all_releases if r.get("role", "").lower() != "main"]
    else:
        filtered = [r for r in all_releases if r.get("role", "").lower() == "main"]

    paginator = Paginator(filtered, 8)
    paginated = paginator.get_page(current_page)

    with ThreadPoolExecutor(max_workers=10) as executor:
        enhanced_releases = list(executor.map(lambda r: fetch_cover_image(r, session), paginated))

    context = {
        "artist": {
            "name": result["title"],
            "image_url": detail.get("images", [{}])[0].get("uri", ""),
            "profile": detail.get("profile", "")
        },
        "releases": enhanced_releases,
        "current_page": current_page,
        "total_pages": paginator.num_pages,
        "mode": mode,
        "has_previous": paginated.has_previous(),
        "has_next": paginated.has_next(),
        "previous_page_number": paginated.previous_page_number() if paginated.has_previous() else None,
        "next_page_number": paginated.next_page_number() if paginated.has_next() else None,
    }

    return render(request, "artists/artist_detail.html", context)

