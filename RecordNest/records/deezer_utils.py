import requests
from django.conf import settings
from base64 import b64encode
from requests.utils import quote
import re
import unicodedata


def clean_artist_name(name):
    return re.sub(r'\s*\(\d+\)$', '', name).strip()


def normalize(name):
    return name.lower().replace("&", "and").replace("-", "").strip()

def normalize_name(name):

    name = name.lower()
    name = name.replace(" and ", " & ")  # cambia and por &
    name = name.replace("feat.", "")
    name = name.replace("featuring", "")
    name = re.sub(r'\s+', ' ', name)  # quita espacios múltiples
    return name.strip()


def get_preview_url_from_deezer(title, artist):
    query = f"{title} {artist}"
    search_url = f"https://api.deezer.com/search?q={quote(query)}"

    try:
        response = requests.get(search_url)
        if response.status_code != 200:
            print(f"Deezer error: {response.status_code}")
            return None

        data = response.json()
        results = data.get("data", [])

        def similarity(a, b):
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()

        best_match = None
        best_score = 0.0

        for track in results:
            track_title = track.get("title", "")
            track_artist = track.get("artist", {}).get("name", "")

            score = similarity(track_title, title) + similarity(track_artist, artist)
            if score > best_score and track.get("preview"):
                best_match = track
                best_score = score

        if best_match:
            return {
                "preview_url": best_match["preview"],
                "deezer_link": best_match["link"],
                "deezer_artists": [best_match.get("artist", {}).get("name", "")]
            }

        return None

    except Exception as e:
        print(f"❌ Error al consultar Deezer: {e}")
        return None
    

def get_deezer_results(track_title, artist_name):

    def search_on_deezer(query):
        try:
            response = requests.get("https://api.deezer.com/search", params={"q": query})
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            print(f"❌ Error en la búsqueda de Deezer: {e}")
            return []

    # 1. Búsqueda con nombre original
    original_query = f"{track_title} {artist_name}"
    results = search_on_deezer(original_query)
    if results:
        return results

    # 2. Reintento: reemplazar ' and ' por ' & '
    if " and " in artist_name.lower():
        alt_artist_name = artist_name.replace(" and ", " & ")
        alt_query = f"{track_title} {alt_artist_name}"
        results = search_on_deezer(alt_query)
        if results:
            return results

    # 3. Reintento: reemplazar '&' por 'and' (por si acaso Deezer tiene el otro formato)
    if " & " in artist_name:
        alt_artist_name = artist_name.replace(" & ", " and ")
        alt_query = f"{track_title} {alt_artist_name}"
        results = search_on_deezer(alt_query)
        if results:
            return results

    return []
    
