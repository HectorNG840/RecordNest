import time
import requests
import numpy as np
import re
from collections import Counter
from django.conf import settings
from sentence_transformers import SentenceTransformer, util
from sklearn.preprocessing import MinMaxScaler
from collection.models import UserRecord, FavoriteRecord, Wishlist, CachedMaster, ExcludedRecommendation, CachedRelease, CachedMaster, UserProfileEmbedding
from records.utils import get_oauth_session
import torch
from concurrent.futures import ThreadPoolExecutor
import logging
import random

DISCOGS_API_URL = "https://api.discogs.com"

# --- Modelo semántico ---
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
logger = logging.getLogger(__name__)


# --- Helpers ---
def clean_text(text):
    if not text:
        return ""
    return re.sub(r"[^\w\s]", "", str(text).lower())


def get_decade(year):
    try:
        y = int(year)
        return f"{y // 10 * 10}s"
    except:
        return ""


def build_features(record):
    return " ".join([
        clean_text(record.title),
        clean_text(record.genres),
        clean_text(record.styles),
        clean_text(record.labels),
        " ".join(clean_text(a.name) for a in record.artists.all()),
        clean_text(get_decade(record.year))
    ])



def fetch_master_details(master_id, session=None, is_release=False):
    """
    Devuelve los detalles de un master o release con cacheo en DB.
    """
    if not session:
        session = get_oauth_session()

    if is_release:
        try:
            cached = CachedRelease.objects.get(release_id=str(master_id))
            return cached.data
        except CachedRelease.DoesNotExist:
            pass
        url = f"{DISCOGS_API_URL}/releases/{master_id}"
    else:
        try:
            cached = CachedMaster.objects.get(master_id=str(master_id))
            return cached.data
        except CachedMaster.DoesNotExist:
            pass
        url = f"{DISCOGS_API_URL}/masters/{master_id}"

    retries = 3
    for attempt in range(retries):
        resp = session.get(url)
        if resp.status_code == 200:
            data = resp.json()
            if is_release:
                CachedRelease.objects.create(release_id=str(master_id), data=data)
            else:
                CachedMaster.objects.create(master_id=str(master_id), data=data)
            return data
        elif resp.status_code == 429:
            wait_time = 2 ** attempt
            print(f"⚠️ Rate limit alcanzado. Esperando {wait_time}s…")
            time.sleep(wait_time)
        else:
            break

    return {}



def build_candidate_features(details):
    parts = []
    parts.append(details.get("title", ""))
    artists = [a.get("name", "") for a in details.get("artists", [])]
    parts.append(" ".join(artists))
    parts.extend(details.get("genres", []))
    parts.extend(details.get("styles", []))
    parts.append(str(details.get("year", "")))
    labels = [l.get("name", "") for l in details.get("labels", [])]
    parts.extend(labels)
    if "tracklist" in details:
        parts.extend([t.get("title", "") for t in details["tracklist"]])
    if details.get("notes"):
        parts.append(details["notes"])
    if details.get("country"):
        parts.append(details["country"])
    return " ".join(parts)


def mmr(doc_embeddings, user_embedding, candidates, lambda_param=0.7, top_n=20):
    selected = []
    candidate_indices = list(range(len(candidates)))

    while len(selected) < top_n and candidate_indices:
        mmr_scores = []
        for i in candidate_indices:
            sim_to_user = util.cos_sim(user_embedding, doc_embeddings[i]).item()
            sim_to_selected = max([util.cos_sim(doc_embeddings[i], doc_embeddings[j]).item() 
                                   for j in selected], default=0)
            score = lambda_param * sim_to_user - (1 - lambda_param) * sim_to_selected
            mmr_scores.append((score, i))
        mmr_scores.sort(reverse=True)
        best = mmr_scores[0][1]
        selected.append(best)
        candidate_indices.remove(best)

    return [candidates[i] for i in selected]


# --- Candidatos a partir de artistas ---
def fetch_candidates_from_artists(user_records, limit=400):
    session = get_oauth_session()
    candidates = []

    def _safe_get(url):
        try:
            resp = session.get(url)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"⚠️ Error en _safe_get: {e}")
        return {}

    artist_counter = Counter(
        artist.name.strip()
        for r in user_records
        for artist in r.artists.all()
        if artist.name.strip()
    )
    all_artists = [a for a, _ in artist_counter.most_common(30)]
    selected_artists = random.sample(all_artists, min(len(all_artists), 10))


    all_genres, all_styles = [], []
    for r in user_records:
        if r.genres:
            all_genres.extend([g.strip().lower() for g in r.genres.split(",")])
        if r.styles:
            all_styles.extend([s.strip().lower() for s in r.styles.split(",")])


    top_genres = [g for g, _ in Counter(all_genres).most_common(5)]
    top_styles = [s for s, _ in Counter(all_styles).most_common(5)]
    selected_tags = set(top_genres + top_styles)

    seen_artists = set()
    seen_tags = set()

    # --- Búsqueda por artistas ---
    for artist_name in selected_artists:
        if not artist_name or artist_name in seen_artists:
            continue

        print(f"Buscando artista: {artist_name}")
        search_url = f"{DISCOGS_API_URL}/database/search"
        resp = requests.get(search_url, params={
            "q": artist_name,
            "per_page": 1,
            "page": 1,
            "key": settings.DISCOGS_CONSUMER_KEY,
            "secret": settings.DISCOGS_CONSUMER_SECRET,
        })
        results = resp.json().get("results", []) if resp.status_code == 200 else []
        if not results:
            print(f"No encontrado en Discogs: {artist_name}")
            continue

        artist_id = results[0]["id"]
        seen_artists.add(artist_name)

        releases_url = f"{DISCOGS_API_URL}/artists/{artist_id}/releases?per_page=50&page=1"
        releases = _safe_get(releases_url).get("releases", [])
        for rel in releases:
            rel["reason"] = f"Del mismo artista {artist_name}"
        candidates.extend(releases)

    # --- Búsqueda por géneros y estilos (solo top seleccionados) ---
    for genre_or_style in selected_tags:
        if genre_or_style in seen_tags:
            continue
        seen_tags.add(genre_or_style)

        print(f"Buscando por género/estilo: {genre_or_style}")
        search_url = f"{DISCOGS_API_URL}/database/search"
        resp = requests.get(search_url, params={
            "q": genre_or_style,
            "type": "master",
            "per_page": 25,
            "page": 1,
            "key": settings.DISCOGS_CONSUMER_KEY,
            "secret": settings.DISCOGS_CONSUMER_SECRET,
        })
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            for res in results:
                res["reason"] = f"Relacionado con tu género/estilo: {genre_or_style}"
            candidates.extend(results)

    # --- Fallback: géneros populares si no hay suficientes ---
    if len(candidates) < 50:
        backups = ["Funk", "Soul", "Electronic", "Jazz", "Pop", "Hip Hop"]
        for backup in random.sample(backups, 2):
            print(f"Buscando por género popular de respaldo: {backup}")
            resp = requests.get(f"{DISCOGS_API_URL}/database/search", params={
                "type": "master",
                "genre": backup,
                "sort": "want",
                "per_page": 25,
                "page": 1,
                "key": settings.DISCOGS_CONSUMER_KEY,
                "secret": settings.DISCOGS_CONSUMER_SECRET,
            })
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                for res in results:
                    res["reason"] = f"Popular en {backup}"
                candidates.extend(results)

    print(f"Total candidatos iniciales: {len(candidates)}")

    # --- Eliminar duplicados (clave = id/master_id) ---
    unique_candidates = list({
        str(c.get("id") or c.get("master_id")): c
        for c in candidates
    }.values())

    return unique_candidates[:limit]



def build_reason(details, user_top_genres, user_top_styles, user_artists):
    reason_parts = []
    cand_genres = set(details.get("genres", []))
    cand_styles = set(details.get("styles", []))
    cand_artists = [a.get("name", "").lower() for a in details.get("artists", [])]

    # Coincidencia de artista
    if any(a.lower() in user_artists for a in cand_artists):
        reason_parts.append("Del mismo artista que ya tienes")

    # Coincidencia de género
    if cand_genres & set(user_top_genres):
        reason_parts.append(f"Coincide en género: {', '.join(cand_genres & set(user_top_genres))}")

    # Coincidencia de estilo
    if cand_styles & set(user_top_styles):
        reason_parts.append(f"Coincide en estilo: {', '.join(cand_styles & set(user_top_styles))}")

    # Año / década
    if details.get("year"):
        reason_parts.append(f"De la década de {str(details['year'])[:3]}0s")

    return " | ".join(reason_parts) if reason_parts else "Relacionado con tu colección"

def update_user_profile(user):

    user_records = UserRecord.objects.filter(user=user)
    if not user_records.exists():
        return None

    texts = [build_features(r) for r in user_records]
    embeddings = model.encode(texts, normalize_embeddings=True)
    profile = np.mean(embeddings, axis=0)

    UserProfileEmbedding.objects.update_or_create(
        user=user,
        defaults={"vector": profile.tolist()}
    )
    return profile

def recommend_records(user, top_n=20):
    user_records = UserRecord.objects.filter(user=user)
    if not user_records.exists():
        return []

    # --- Artistas en colección ---
    collection_artists = set(
        a.name.strip().lower()
        for r in user_records
        for a in r.artists.all()
    )

    # --- Exclusiones ---
    exclude_master_ids = set(
        Wishlist.objects.filter(user=user).values_list("discogs_master_id", flat=True)
    )
    excluded_ids = set(
        ExcludedRecommendation.objects.filter(user=user).values_list("master_id", flat=True)
    )
    exclude_titles_artists = set(
        (r.title.strip().lower(), a.name.strip().lower())
        for r in user_records
        for a in r.artists.all()
    )

    # --- Perfil usuario ---
    texts = []
    favs = []
    try:
        f = FavoriteRecord.objects.get(user=user)
        favs = [f.record_1, f.record_2, f.record_3]
        favs = [rec for rec in favs if rec is not None]
    except FavoriteRecord.DoesNotExist:
        pass

    for r in user_records:
        texts.append(build_features(r))

    # --- Top géneros y estilos del usuario ---
    all_genres, all_styles = [], []
    for r in user_records:
        if r.genres:
            all_genres.extend([g.strip() for g in r.genres.split(",")])
        if r.styles:
            all_styles.extend([s.strip() for s in r.styles.split(",")])

    top_genres = [g for g, _ in Counter(all_genres).most_common(6)]
    top_styles = [s for s, _ in Counter(all_styles).most_common(6)]

    # --- Candidatos ---
    candidates = fetch_candidates_from_artists(user_records)[:75]
    print(f"Candidatos obtenidos: {len(candidates)}")

    session = get_oauth_session()
    with ThreadPoolExecutor(max_workers=20) as executor:
        details_list = list(executor.map(
            lambda c: fetch_master_details(
                c.get("master_id") or (c.get("basic_information", {}).get("master_id") if "basic_information" in c else None) or c.get("id"),
                session,
                is_release=not bool(c.get("master_id"))
            ),
            candidates
        ))

    # --- Filtrado ---
    candidate_texts, valid_candidates = [], []
    for c, details in zip(candidates, details_list):
        master_id = str(c.get("master_id") or c.get("id"))
        if not details or not master_id:
            continue
        if master_id in exclude_master_ids or master_id in excluded_ids:
            continue

        cand_title = details.get("title", "").strip().lower()
        cand_artist = details.get("artists", [{}])[0].get("name", "").strip().lower()
        if (cand_title, cand_artist) in exclude_titles_artists:
            continue

        candidate_texts.append(build_candidate_features(details))
        valid_candidates.append((c, details))

    if not candidate_texts:
        return []

    # --- Embeddings ---
    try:
        user_profile = np.array(user.profile_embedding.vector, dtype=np.float32)
    except UserProfileEmbedding.DoesNotExist:
        user_profile = update_user_profile(user)
        if user_profile is None:
            return []

    cand_vecs = model.encode(candidate_texts, normalize_embeddings=True, convert_to_tensor=True)

    similarities = util.cos_sim(cand_vecs, torch.tensor(user_profile)).cpu().numpy().ravel()
    sim_scaled = MinMaxScaler().fit_transform(similarities.reshape(-1, 1)).ravel()

    # --- Ranking híbrido ---
    recs = []
    for (c, details), sim in zip(valid_candidates, sim_scaled):
        comm = details.get("community", {})
        have, want = comm.get("have", 0), comm.get("want", 0)
        rating = comm.get("rating", {}).get("average", 0) or 0

        popularity = (have + want) / 2000.0
        popularity_score = min(1.0, (0.5 * popularity + 0.5 * (rating / 5.0)))
        collaborative_score = min(1.0, want / (have + 1))
        novelty = 1 / (1 + popularity)

        final_score = (
            0.6 * float(sim) +
            0.2 * popularity_score +
            0.1 * collaborative_score +
            0.1 * novelty
        )

        # Penalizar artistas ya en colección
        artist_name = details.get("artists", [{}])[0].get("name", "Unknown")
        if artist_name.strip().lower() in collection_artists:
            final_score *= 0.5

        recs.append({
            "title": details.get("title"),
            "artists": artist_name,
            "year": details.get("year", "Desconocido"),
            "genres": ", ".join(details.get("genres", [])),
            "styles": ", ".join(details.get("styles", [])),
            "labels": ", ".join([l.get("name") for l in details.get("labels", [])]) if details.get("labels") else "",
            "cover_image": details.get("images", [{}])[0].get("uri") if details.get("images") else c.get("cover_image"),
            "master_id": details.get("id") if "masters_url" in details else details.get("master_id"),
            "release_id": details.get("id") if "masters_url" not in details else None,
            "similarity": round(final_score, 3),
            "reason": build_reason(details, top_genres, top_styles, collection_artists)
        })

    print(f"Recomendaciones iniciales: {len(recs)}")

    # --- Limitar repetición de artistas ---
    artist_counts = {}
    unique_artist_recs = []
    for rec in sorted(recs, key=lambda x: x["similarity"], reverse=True):
        a = rec["artists"].strip().lower()
        if a in collection_artists and artist_counts.get(a, 0) >= 2:
            continue
        artist_counts[a] = artist_counts.get(a, 0) + 1
        unique_artist_recs.append(rec)

    recs = unique_artist_recs
    print(f"Tras limitar repetición de artistas: {len(recs)}")

    # --- Diversidad por género ---
    genre_counts = {}
    diverse_recs = []
    for rec in sorted(recs, key=lambda x: x["similarity"], reverse=True):
        g = rec["genres"].split(",")[0] if rec["genres"] else "Unknown"
        if genre_counts.get(g, 0) >= 10:
            continue
        genre_counts[g] = genre_counts.get(g, 0) + 1
        diverse_recs.append(rec)

    # --- Rellenar si faltan ---
    if len(diverse_recs) < top_n:
        faltan = top_n - len(diverse_recs)
        extra = [r for r in recs if r not in diverse_recs][:faltan]
        diverse_recs.extend(extra)

    print(f"Tras aplicar diversidad de género + relleno: {len(diverse_recs)}")

    # --- Diversificación final con MMR ---
    rec_embeddings = model.encode(
        [r["title"] + " " + r["artists"] for r in diverse_recs], 
        normalize_embeddings=True, convert_to_tensor=True
    )
    final_recs = mmr(rec_embeddings, user_profile, diverse_recs, lambda_param=0.7, top_n=top_n)

    print(f"Recomendaciones finales: {len(final_recs)}")
    return final_recs




