from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import UserRecord, Track, Tag
import json

@login_required
def add_to_collection(request):
    if request.method == "POST":
        data = request.POST

        user_record = UserRecord.objects.create(
            user=request.user,
            title=data.get("title"),
            artists=data.get("artists"),
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

        tag_names = [t.strip() for t in data.get("tags", "").split(",") if t.strip()]
        tag_objs = []
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name, user=request.user)
            tag_objs.append(tag)
        user_record.tags.set(tag_objs)

        try:
            tracklist_raw = request.POST.get("tracklist_json")
            print("📥 tracklist_json raw:", tracklist_raw)
            tracklist_data = json.loads(tracklist_raw)
            for t in tracklist_data:
                Track.objects.create(
                    record=user_record,
                    position=t.get("position", ""),
                    title=t.get("title", ""),
                    duration=t.get("duration", ""),
                    preview_url=t.get("preview_url", "") or "",
                    deezer_link=t.get("deezer_link", "") or "",
                    deezer_artists=", ".join(t.get("deezer_artists", []))
                )
                print(f"✅ Track guardado: {t.get('title')}")
        except json.JSONDecodeError as e:
            print("❌ Error decoding tracklist JSON:", e)

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
    records = UserRecord.objects.filter(user=user)

    if tag_id:
        try:
            records = records.filter(tags__id=tag_id)
        except ValueError:
            pass  # fallback seguro si el id no es válido

    user_tags = Tag.objects.filter(user=user)
    return render(request, "collection/collection_list.html", {
        "records": records,
        "tags": user_tags,
        "selected_tag": int(tag_id) if tag_id else None,
    })

@login_required
def local_record_detail(request, record_id):
    record = get_object_or_404(UserRecord, id=record_id, user=request.user)
    tracks = record.tracks.all().order_by("position")

    user_tags = Tag.objects.filter(user=request.user)

    
    return render(request, "records/local_record_detail.html", {
        "record": record,
        "tracks": tracks,
        "user_tags": user_tags,  # 👈 pásalas al contexto
    })

@login_required
def add_tag(request, record_id):
    if request.method == "POST":
        record = get_object_or_404(UserRecord, id=record_id, user=request.user)
        tag_id = request.POST.get("existing_tag")
        new_tag_name = request.POST.get("new_tag")

        # Si viene una nueva tag, créala
        if new_tag_name:
            tag, _ = Tag.objects.get_or_create(name=new_tag_name.strip(), user=request.user)
            record.tags.add(tag)

        # Si seleccionó una existente (por ID)
        elif tag_id:
            try:
                tag = Tag.objects.get(id=int(tag_id), user=request.user)
                record.tags.add(tag)
            except (Tag.DoesNotExist, ValueError):
                pass  # Evita crasheo si tag no existe o ID inválido

        # Si el record tenía solo "Sin etiquetas", elimínala
        sin_etiquetas = Tag.objects.filter(name="Sin etiquetas", user=request.user).first()
        if sin_etiquetas in record.tags.all():
            record.tags.remove(sin_etiquetas)

        return redirect("local_record_detail", record_id=record.id)

@login_required
@require_POST
def remove_tag(request, record_id, tag_id):
    record = get_object_or_404(UserRecord, id=record_id, user=request.user)
    tag = get_object_or_404(Tag, id=tag_id, user=request.user)
    record.tags.remove(tag)

    # Si no quedan tags, añade "Sin etiquetas"
    if record.tags.count() == 0:
        default_tag, _ = Tag.objects.get_or_create(name="Sin etiquetas", user=request.user)
        record.tags.add(default_tag)

    return redirect("local_record_detail", record_id=record.id)

