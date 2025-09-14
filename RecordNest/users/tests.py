
import pytest
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from users.models import CustomUser


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="tester",
        email="tester@example.com",
        password="password123",
        name="Test User"
    )


@pytest.mark.django_db
def test_signup_view_get(client):
    url = reverse("signup")
    response = client.get(url)
    assert response.status_code == 200
    assert "users/signup.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_signup_view_post(client):
    url = reverse("signup")
    response = client.post(url, {
        "username": "newuser",
        "name": "Nuevo Usuario",
        "email": "newuser@example.com",
        "birthday": "2000-01-01",
        "password1": "ComplexPass123!",
        "password2": "ComplexPass123!",
    })
    assert response.status_code == 302  # redirect al login
    assert CustomUser.objects.filter(username="newuser").exists()


@pytest.mark.django_db
def test_login_and_logout(client, user):
    logout_url = reverse("logout")
    logged_in = client.login(username=user.username, password="password123")
    assert logged_in is True

    # 🔹 Usar POST para logout
    response = client.post(logout_url)
    assert response.status_code == 302


@pytest.mark.django_db
def test_profile_view(client, user):
    client.force_login(user)
    url = reverse("profile", args=[user.username])
    response = client.get(url)
    assert response.status_code == 200
    assert "users/profile.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_edit_profile_view(client, user):
    client.force_login(user)
    url = reverse("edit_profile")
    response = client.post(url, {
        "name": "Nuevo Nombre",
        "email": user.email,
        "birthday": "2000-01-01",
        "bio": "Nueva biografía",
        "cropped_image_data": "",
    })
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.name == "Nuevo Nombre"


@pytest.mark.django_db
def test_delete_profile_view(client, user):
    client.force_login(user)
    url = reverse("delete_profile")
    response = client.post(url)
    assert response.status_code == 302
    assert not CustomUser.objects.filter(id=user.id).exists()


@pytest.mark.django_db
def test_activate_view(client, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    url = reverse("activate", args=[uid, token])
    response = client.get(url)
    assert response.status_code == 200 or response.status_code == 302
    user.refresh_from_db()
    assert user.is_active


@pytest.mark.django_db
def test_user_search_view(client, user):
    client.force_login(user)
    url = reverse("user_search") + "?q=test"
    response = client.get(url)
    assert response.status_code == 200
    assert "users/social_search.html" in [t.name for t in response.templates]
