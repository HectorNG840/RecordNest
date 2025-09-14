import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from collection.models import Tag, Artist, UserRecord, Track, RecordList, Wishlist
from collection.forms import RecordListForm
from django.contrib.auth import get_user_model


# Fixtures
User = get_user_model()

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser",
        password="password123",
        email="test@example.com"
    )


@pytest.fixture
def artist():
    return Artist.objects.create(name="Miles Davis", discogs_id="123")


@pytest.fixture
def tag(user):
    return Tag.objects.create(name="Jazz", user=user)


@pytest.fixture
def user_record(user, artist, tag):
    record = UserRecord.objects.create(user=user, title="Kind of Blue", year="1959")
    record.artists.add(artist)
    record.tags.add(tag)
    return record



@pytest.mark.django_db
def test_create_userrecord_with_relations(user_record):
    assert user_record.title == "Kind of Blue"
    assert user_record.artists.count() == 1
    assert user_record.tags.count() == 1


@pytest.mark.django_db
def test_track_creation(user_record):
    track = Track.objects.create(record=user_record, position="A1", title="So What")
    assert str(track) == "A1 - So What"


@pytest.mark.django_db
def test_recordlist_creation(user):
    rl = RecordList.objects.create(name="Favoritos", user=user)
    assert str(rl) == "Favoritos"


@pytest.mark.django_db
def test_recordlistform_valid(user):
    form = RecordListForm(data={"name": "Mis listas", "description": "Jazz y más", "is_public": True})
    assert form.is_valid()



@pytest.mark.django_db
def test_add_to_collection(client, user):
    client.force_login(user)
    url = reverse("add_to_collection")
    response = client.post(url, {
        "title": "Blue Train",
        "artists": '[{"name": "John Coltrane", "id": "321"}]',
        "tags": "Jazz, Sax",
        "tracklist_json": '[{"position": "A1", "title": "Blue Train", "duration": "10:43"}]'
    })
    assert response.status_code == 302
    assert UserRecord.objects.filter(user=user, title="Blue Train").exists()


@pytest.mark.django_db
def test_delete_from_collection(client, user, user_record):
    client.force_login(user)
    url = reverse("delete_from_collection", args=[user_record.id])
    response = client.post(url)
    assert response.status_code == 302
    assert not UserRecord.objects.filter(id=user_record.id).exists()


@pytest.mark.django_db
def test_my_collection_view(client, user, user_record):
    client.force_login(user)
    url = reverse("my_collection")
    response = client.get(url)
    assert response.status_code == 200
    assert "records" in response.context
    assert user_record in response.context["records"]


@pytest.mark.django_db
def test_create_list_view(client, user):
    client.force_login(user)
    url = reverse("create_list")
    response = client.post(url, {"name": "Nueva lista", "description": "Mis discos"})
    assert response.status_code == 302
    assert RecordList.objects.filter(user=user, name="Nueva lista").exists()


@pytest.mark.django_db
def test_add_record_to_list(client, user, user_record):
    client.force_login(user)
    record_list = RecordList.objects.create(name="Favoritos", user=user)
    url = reverse("add_record_to_list", args=[user_record.id, record_list.id])
    response = client.get(url)
    assert response.status_code == 302
    assert user_record in record_list.records.all()



@pytest.mark.django_db
def test_remove_from_wishlist(client, user):
    client.force_login(user)
    w = Wishlist.objects.create(user=user, discogs_release_id="999")
    url = reverse("remove_from_wishlist", args=[w.id])
    response = client.get(url)
    assert response.status_code == 302
    assert not Wishlist.objects.filter(id=w.id).exists()



@pytest.mark.django_db
def test_recommendations_empty(client, user):
    client.force_login(user)
    url = reverse("recommendations")
    response = client.get(url)
    assert response.status_code == 400
    assert "colección está vacía" in response.json()["error"]
