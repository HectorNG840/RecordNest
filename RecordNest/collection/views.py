from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .forms import RecordListForm
from .models import UserRecord, Track, Tag, RecordList
import json
import requests
from django.http import JsonResponse

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
                    deezer_artists=", ".join(t.get("deezer_artists", [])),
                    deezer_id=t.get("id", "")
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
            pass
        
    user_lists = RecordList.objects.filter(user=request.user)        
    user_tags = Tag.objects.filter(user=user)
    return render(request, "collection/collection_list.html", {
        "records": records,
        "tags": user_tags,
        "selected_tag": int(tag_id) if tag_id else None,
        'user_lists': user_lists,
    })

@login_required
def local_record_detail(request, record_id):
    record = get_object_or_404(UserRecord, id=record_id, user=request.user)
    tracks = record.tracks.all().order_by("position")

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
def remove_tag(request, record_id, tag_id):
    record = get_object_or_404(UserRecord, id=record_id, user=request.user)
    tag = get_object_or_404(Tag, id=tag_id, user=request.user)
    record.tags.remove(tag)

    
    if record.tags.count() == 0:
        default_tag, _ = Tag.objects.get_or_create(name="Sin etiquetas", user=request.user)
        record.tags.add(default_tag)

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
    return redirect('my_lists')  # Ajusta al nombre de tu URL

@login_required
def edit_list(request, list_id):
    record_list = get_object_or_404(RecordList, id=list_id, user=request.user)
    
    if request.method == 'POST':
        form = RecordListForm(request.POST, instance=record_list)
        if form.is_valid():
            form.save()
            return redirect('my_lists')
    else:
        form = RecordListForm(instance=record_list)

    return render(request, 'collection/edit_list.html', {'list': record_list})

@login_required
def list_detail(request, list_id):
    record_list = get_object_or_404(RecordList, id=list_id, user=request.user)
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


