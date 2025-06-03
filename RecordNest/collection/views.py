from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .models import UserRecord

@login_required
def add_to_collection(request):
    if request.method == "POST":
        record = UserRecord.objects.create(
            user=request.user,
            title=request.POST.get("title", ""),
            artists=request.POST.get("artists", ""),
            year=request.POST.get("year", ""),
            cover_image=request.POST.get("cover_image", ""),
            notes=request.POST.get("notes", "")
        )
        return redirect("my_collection")
    return HttpResponseBadRequest("Solicitud inválida")

@login_required
def my_collection(request):
    records = UserRecord.objects.filter(user=request.user).order_by("-added_at")
    return render(request, "collection/collection_list.html", {"records": records})

@login_required
def local_record_detail(request, pk):
    record = get_object_or_404(UserRecord, pk=pk, user=request.user)
    return render(request, "collection/detail.html", {"record": record})

