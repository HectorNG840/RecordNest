from django.utils import timezone
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .forms import RecordListForm
from .models import UserRecord, Track, Tag, RecordList, Wishlist, ExcludedRecommendation, Artist, CachedRecommendation
import json
import requests
from django.http import JsonResponse
import base64
from django.core.files.base import ContentFile
import uuid
from django.core.exceptions import PermissionDenied
import discogs_client
from django.conf import settings
from discogs_client.exceptions import HTTPError
from .recommender_semantic import recommend_records
from records.views import track_position_key
from records.utils import get_oauth_session, get_discogs_client
from collections import Counter


@login_required
def add_to_collection(request):
    if request.method == "POST":
        data = request.POST

        user_record = UserRecord.objects.create(
            user=request.user,
            title=data.get("title"),
            year=data.get("year", ""),
            cover_image=data.get("cover_image", ""),
            released=data.get("released", ""),
            notes=data.get("notes", ""),
            barcode=data.get("barcode", ""),
            genres=data.get("genres", ""),
            styles=data.get("styles", ""),
            labels=data.get("labels", ""),
            formats=data.get("formats", ""),
        )

        artists_raw = request.POST.get("artists", "[]")
        try:
            artists_data = json.loads(artists_raw)
        except json.JSONDecodeError:
            artists_data = []
        print("data:", artists_data)

        artist_objs = []
        for a in artists_data:
            if isinstance(a, dict):
                name = a.get("name", "").strip()
                discogs_id = a.get("id")
                if discogs_id is not None:
                    discogs_id = str(discogs_id)
            else:
                name = str(a).strip()
                discogs_id = None

            if not name:
                continue

            artist = None

            if discogs_id:
                artist = Artist.objects.filter(discogs_id=discogs_id).first()
                if artist:
                    if artist.name != name:
                        artist.name = name
                        artist.save()

            if not artist:
                artist = Artist.objects.filter(name=name).first()
                if artist:

                    if discogs_id and not artist.discogs_id:
                        artist.discogs_id = discogs_id
                        artist.save()

            if not artist:
                artist = Artist.objects.create(name=name, discogs_id=discogs_id)

            artist_objs.append(artist)
        print("artist_object:", artist_objs)
        if artist_objs:
            print("Antes de set():", user_record.artists.all())  # Debería estar vacío
            user_record.artists.set(artist_objs)
            print("Después de set():", user_record.artists.all())

        tag_names = [t.strip() for t in data.get("tags", "").split(",") if t.strip()]
        tag_objs = []
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name, user=request.user)
            tag_objs.append(tag)
        if tag_objs:
            user_record.tags.set(tag_objs)

        try:
            tracklist_raw = request.POST.get("tracklist_json")
            print("tracklist_json raw:", tracklist_raw)
            tracklist_data = json.loads(tracklist_raw)
            for t in tracklist_data:
                Track.objects.create(
                    record=user_record,
                    position=t.get("position", ""),
                    title=t.get("title", ""),
                    duration=t.get("duration", ""),
                    preview_url=t.get("preview_url", "") or "",
                    deezer_link=t.get("deezer_link", "") or "",
                    deezer_artists=", ".join(t.get("deezer_artists", [])),
                    deezer_id=t.get("id", "")
                )
        except json.JSONDecodeError as e:
            print("Error decoding tracklist JSON:", e)

        return redirect("my_collection")

    return HttpResponseBadRequest("Solicitud inválida")


@login_required
def delete_from_collection(request, record_id):
    if request.method == "POST":
        record = get_object_or_404(UserRecord, id=record_id, user=request.user)
        record.delete()
        return redirect("my_collection")
    return HttpResponseBadRequest("Solicitud inválida")


@login_required
def my_collection(request):
    user = request.user
    tag_id = request.GET.get("tag")
    sort = request.GET.get("sort", "added_at")
    order = request.GET.get("order", "desc")

    records = UserRecord.objects.filter(user=user)

    if tag_id:
        try:
            records = records.filter(tags__id=tag_id)
        except ValueError:
            pass

    if sort == "artists":
        sort_field = "artists__name" if order == "asc" else "-artists__name"
        records = records.order_by(sort_field).distinct()
    elif sort in ["title", "year", "added_at"]:
        sort_field = sort if order == "asc" else f"-{sort}"
        records = records.order_by(sort_field)

    user_lists = RecordList.objects.filter(user=user)
    user_tags = Tag.objects.filter(user=user)

    return render(request, "collection/collection_list.html", {
        "records": records,
        "tags": user_tags,
        "selected_tag": int(tag_id) if tag_id else None,
        "selected_sort": sort,
        "selected_order": order,
        "user_lists": user_lists,
    })

@login_required
def local_record_detail(request, record_id):
    record = get_object_or_404(UserRecord, id=record_id, user=request.user)
    tracks = sorted(record.tracks.all(), key=lambda t: track_position_key(t.position or ""))
    user_tags = Tag.objects.filter(user=request.user)

    return render(request, "records/local_record_detail.html", {
        "record": record,
        "tracks": tracks,
        "user_tags": user_tags,
    })

@login_required
def add_tag(request, record_id):
    if request.method == "POST":
        record = get_object_or_404(UserRecord, id=record_id, user=request.user)
        tag_id = request.POST.get("existing_tag")
        new_tag_name = request.POST.get("new_tag")

        if new_tag_name:
            tag, _ = Tag.objects.get_or_create(name=new_tag_name.strip(), user=request.user)
            record.tags.add(tag)

        elif tag_id:
            try:
                tag = Tag.objects.get(id=int(tag_id), user=request.user)
                record.tags.add(tag)
            except (Tag.DoesNotExist, ValueError):
                pass

        
        sin_etiquetas = Tag.objects.filter(name="Sin etiquetas", user=request.user).first()
        if sin_etiquetas in record.tags.all():
            record.tags.remove(sin_etiquetas)

        return redirect("local_record_detail", record_id=record.id)

@login_required
@require_POST
def add_tag_to_collection(request):
    tag_name = request.POST.get("new_tag_name", "").strip()
    if tag_name:
        Tag.objects.get_or_create(name=tag_name, user=request.user)
    return redirect("my_collection")
    
@login_required
@require_POST
def delete_tag(request, tag_id):
    tag = get_object_or_404(Tag, id=tag_id, user=request.user)

    if tag.records.exists():
        from django.contrib import messages
        messages.error(request, "No puedes eliminar esta etiqueta porque está en uso.")
        return redirect('my_collection')

    tag.delete()
    return redirect('my_collection')


@login_required
@require_POST
def remove_tag(request, record_id, tag_id):
    record = get_object_or_404(UserRecord, id=record_id, user=request.user)
    tag = get_object_or_404(Tag, id=tag_id, user=request.user)
    record.tags.remove(tag)

    

    return redirect("local_record_detail", record_id=record.id)

@login_required
def my_lists(request):
    lists = RecordList.objects.filter(user=request.user)
    return render(request, 'collection/my_lists.html', {'lists': lists})

@login_required
def create_list(request):
    if request.method == 'POST':
        form = RecordListForm(request.POST, request.FILES)
        if form.is_valid():
            record_list = form.save(commit=False)
            record_list.user = request.user
            record_list.save()
            return redirect('my_lists')
    else:
        form = RecordListForm()
    return render(request, 'collection/create_list.html', {'form': form})

@login_required
def add_record_to_list(request, record_id, list_id):
    record_list = get_object_or_404(RecordList, id=list_id, user=request.user)
    record = get_object_or_404(UserRecord, id=record_id, user=request.user)
    record_list.records.add(record)
    return redirect('my_lists')

@login_required
def delete_list(request, list_id):
    record_list = get_object_or_404(RecordList, id=list_id, user=request.user)
    record_list.delete()
    return redirect('my_lists')


@login_required
def edit_list(request, list_id):
    record_list = get_object_or_404(RecordList, id=list_id, user=request.user)

    if request.method == 'POST':
        form = RecordListForm(request.POST, request.FILES, instance=record_list)

        if form.is_valid():

            record_list = form.save(commit=False)

            cropped_data = request.POST.get('cropped_image_data')
            if cropped_data and cropped_data.startswith('data:image'):
                format, imgstr = cropped_data.split(';base64,')
                ext = format.split('/')[-1]
                file_name = f"list_cover_{record_list.id}.{ext}"
                record_list.cover_image.save(file_name, ContentFile(base64.b64decode(imgstr)), save=False)


            record_list.save()
            return redirect('list_detail', list_id=record_list.id)

    else:
        form = RecordListForm(instance=record_list)

    return render(request, 'collection/edit_list.html', {
        'form': form,
        'record_list': record_list
    })


@login_required
def list_detail(request, list_id):
    record_list = get_object_or_404(RecordList, id=list_id)

    if not record_list.is_public and record_list.user != request.user:
        raise PermissionDenied("No tienes permiso para ver esta lista.")

    records = record_list.records.all()

    return render(request, 'collection/list_detail.html', {
        'record_list': record_list,
        'records': records
    })

@login_required
def remove_record_from_list(request, list_id, record_id):
    record_list = get_object_or_404(RecordList, id=list_id, user=request.user)
    record = get_object_or_404(UserRecord, id=record_id, user=request.user)

    if request.method == "POST":
        record_list.records.remove(record)
        return redirect('list_detail', list_id=list_id)

    return redirect('my_lists')


def fetch_preview_url(request, track_id):
    if request.method == "GET":
        try:
            response = requests.get(f"https://api.deezer.com/track/{track_id}")
            data = response.json()
            return JsonResponse({'preview': data.get("preview")})
        except Exception:
            return JsonResponse({'preview': None}, status=500)
        


@login_required
def add_to_wishlist(request, discogs_id):
    try:
        d = get_discogs_client()

        print(f"Intentando añadir a wishlist con el ID: {discogs_id}")


        expected_title = request.GET.get('title', '').strip()


        try:
            print(f"Intentando obtener el disco {discogs_id} como release_id")
            release = d.release(discogs_id)  
            print(f"Disco {discogs_id} es un release.")

            if release.title.strip().lower() == expected_title.lower():
                print(f"El título coincide con el disco esperado: {expected_title}")

                if hasattr(release, 'master_id') and release.master_id:
                    print(f"Este release tiene un master_id: {release.master_id}")

                    Wishlist.objects.create(user=request.user, discogs_master_id=release.master_id)
                    return redirect('user_wishlist')
                else:
                    print(f"Este release con ID {discogs_id} no tiene master_id.")

                    Wishlist.objects.create(user=request.user, discogs_release_id=discogs_id)
                    return redirect('user_wishlist')
            else:
                print(f"El título del release no coincide con el título esperado: {expected_title} != {release.title.strip()}")
                print(f"Intentando con el master_id para el disco {discogs_id}")
                

                try:
                    print(f"Disco {discogs_id} es un master. Guardando en master_id.")
                    Wishlist.objects.create(user=request.user, discogs_master_id=discogs_id)
                    return redirect('user_wishlist')
                except HTTPError as e2:

                    if e2.status_code == 404:
                        print(f"Disco {discogs_id} no existe ni como master ni como release.")
                        return HttpResponse(f"El disco con ID {discogs_id} no se encuentra.")
                    else:
                        raise 

        except HTTPError as e:

            if e.status_code == 404:
                print(f"Disco {discogs_id} no es un release_id, intentando como master_id.")
                try:
                    master = d.master(discogs_id)
                    print(f"Disco {discogs_id} es un master. Guardando en master_id.")
                    Wishlist.objects.create(user=request.user, discogs_master_id=discogs_id)
                    return redirect('user_wishlist')
                except HTTPError as e2:

                    if e2.status_code == 404:
                        print(f"Disco {discogs_id} no existe ni como master ni como release.")
                        return HttpResponse(f"El disco con ID {discogs_id} no se encuentra.")
                    else:
                        raise
            else:
                raise

    except Exception as e:

        print(f"Error al añadir a wishlist: {e}")
        return HttpResponse(f"Error al añadir a wishlist: {e}")



@login_required
def remove_from_wishlist(request, wishlist_id):
    if not request.user.is_authenticated:
        return redirect('login')


    wishlist_item = get_object_or_404(Wishlist, id=wishlist_id, user=request.user)
    

    wishlist_item.delete()

    return redirect('user_wishlist')



@login_required
def user_wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    records = []

    for item in wishlist_items:
        try:
            d = get_discogs_client()

            if item.discogs_master_id:
                print(f"Recuperando disco con master_id: {item.discogs_master_id}")
                master = d.master(item.discogs_master_id)
                release = master.main_release
                release.refresh()

                cover_image = release.images[0]['uri'] if release.images else '/static/images/placeholder-image.png'

                record = {
                    'title': release.title if release.title else "Sin título",
                    'artists': [artist.name for artist in release.artists] if release.artists else [],
                    'year': release.year if release.year else "Desconocido",
                    'genres': list(release.genres) if release.genres else [],
                    'formats': [fmt['name'] for fmt in release.formats] if release.formats else [],
                    'cover_image': cover_image,
                    'master_id': item.discogs_master_id,
                    'wishlist_id': item.id
                }
                records.append(record)

            elif item.discogs_release_id:
                print(f"Recuperando disco con release_id: {item.discogs_release_id}")
                release = d.release(item.discogs_release_id)
                release.refresh()

                cover_image = release.images[0]['uri'] if release.images else '/static/images/placeholder-image.png'

                record = {
                    'title': release.title if release.title else "Sin título",
                    'artists': [artist.name for artist in release.artists] if release.artists else [],
                    'year': release.year if release.year else "Desconocido",
                    'genres': list(release.genres) if release.genres else [],
                    'formats': [fmt['name'] for fmt in release.formats] if release.formats else [],
                    'cover_image': cover_image,
                    'release_id': item.discogs_release_id,
                    'wishlist_id': item.id
                }
                records.append(record)

        except Exception as e:
            print(f"Error al obtener datos de Discogs para ID {item.discogs_master_id or item.discogs_release_id}: {e}")
            continue

    return render(request, 'collection/user_wishlist.html', {'records': records})


@login_required
def recommendations(request):
    user = request.user
    user_records = UserRecord.objects.filter(user=user)

    if not user_records.exists():
        return JsonResponse(
            {"error": "Tu colección está vacía, añade discos para obtener recomendaciones."},
            status=400
        )

    try:
        cache = getattr(user, "cached_recommendations", None)

        if cache and cache.data:
            recs = cache.data
        else:
            recs = recommend_records(user, top_n=14)
            CachedRecommendation.objects.update_or_create(
                user=user,
                defaults={"data": recs, "updated_at": timezone.now()}
            )

        return JsonResponse({"recommendations": recs})
    except Exception as e:
        return JsonResponse(
            {"error": f"Ocurrió un error en el sistema de recomendaciones: {str(e)}"},
            status=500
        )


@login_required
def recommendations_api(request):
    limit = int(request.GET.get("limit", 14))
    user = request.user

    cache = getattr(user, "cached_recommendations", None)

    if cache and cache.data:
        recs = cache.data[:limit]
    else:
        recs = recommend_records(user, top_n=limit)
        CachedRecommendation.objects.update_or_create(
            user=user,
            defaults={"data": recs, "updated_at": timezone.now()}
        )

    return JsonResponse({"recommendations": recs})
    
@login_required
def recommendations_page(request):
    return render(request, "collection/recommendations.html")


@login_required
def exclude_recommendation(request, master_id):
    if request.method == "POST":
        ExcludedRecommendation.objects.get_or_create(
            user=request.user,
            master_id=master_id
        )
    return redirect("recommendations_semantic")
