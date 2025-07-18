from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import login
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils.encoding import force_str
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
import base64
from django.core.files.base import ContentFile
from records.models import Record
from collection.models import UserRecord, FavoriteRecord, RecordList
from django.db.models import Q



from .forms import CustomUserCreationForm, ProfileUpdateForm
from .models import CustomUser

def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.set_password(form.cleaned_data["password1"])
            user.save()

            current_site = get_current_site(request)
            subject = 'Activa tu cuenta en RecordNest'
            message = render_to_string('users/account_activation_email.html', {
                'user': user,
                'domain': "127.0.0.1:8000",
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
            messages.success(request, "Registro exitoso. Revisa tu correo para activar tu cuenta.")
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/signup.html', {'form': form})

@login_required
def profile(request, username):
    user_profile = get_object_or_404(CustomUser, username=username)

    favorite_obj, _ = FavoriteRecord.objects.get_or_create(user=user_profile)

    if request.user == user_profile:
        user_lists = RecordList.objects.filter(user=user_profile)
    else:
        user_lists = RecordList.objects.filter(user=user_profile, is_public=True)

    favorite_records = [
        favorite_obj.record_1,
        favorite_obj.record_2,
        favorite_obj.record_3,
    ]

    return render(request, "users/profile.html", {
        "viewer": request.user,
        "profile_user": user_profile,
        "favorite_records": favorite_records,
        "user_lists": user_lists,
    })
    
def activate(request, uidb64, token):
    user = None

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except Exception as e:
        print("❌ Error al decodificar UID:", e)
        messages.error(request, "Enlace inválido.")
        return redirect("login")

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        return render(request, "users/activation_success.html")
        messages.success(request, "✅ Cuenta activada correctamente. Ya puedes iniciar sesión.")
    else:
        messages.error(request, "❌ El enlace de activación no es válido o ha expirado.")

    return redirect("login")

@login_required
def edit_profile(request):
    user = request.user

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        cropped_data = request.POST.get("cropped_image_data")

        print("Recibido:", request.POST.get("cropped_image_data")[:100])

        if form.is_valid():
            if cropped_data:
                format, imgstr = cropped_data.split(';base64,')
                ext = format.split('/')[-1]
                file_name = f"profile_{user.username}.{ext}"
                image_file = ContentFile(base64.b64decode(imgstr), name=file_name)
                user.profile_image = image_file

            form.save()
            return redirect('profile', username=user.username)

    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, "users/edit_profile.html", {"form": form})

@login_required
def select_favorite_record(request, slot):
    user = request.user
    favorite_obj, _ = FavoriteRecord.objects.get_or_create(user=user)

    if request.method == 'POST':
        record_id = request.POST.get('record_id')
        try:
            record = UserRecord.objects.get(id=record_id, user=user)
            if slot == 1:
                favorite_obj.record_1 = record
            elif slot == 2:
                favorite_obj.record_2 = record
            elif slot == 3:
                favorite_obj.record_3 = record
            favorite_obj.save()
        except UserRecord.DoesNotExist:
            pass
        return redirect('profile', username=user.username)

    # Si GET, mostrar formulario
    user_records = UserRecord.objects.filter(user=user)
    return render(request, 'users/select_favourite_record.html', {
        'slot': slot,
        'user_records': user_records
    })

@login_required
def user_search(request):
    query = request.GET.get("q", "")
    users = []

    if query:
        users = CustomUser.objects.filter(
            Q(username__icontains=query) | Q(name__icontains=query)
        ).exclude(id=request.user.id)

    return render(request, "users/social_search.html", {
        "query": query,
        "results": users
    })