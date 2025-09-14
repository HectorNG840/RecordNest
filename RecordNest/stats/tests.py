import pytest
from django.urls import reverse
from django.utils import timezone
from users.models import CustomUser
from collection.models import UserRecord, Wishlist, Artist


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="tester",
        email="tester@example.com",
        password="password123"
    )


@pytest.fixture
def artist(db):
    return Artist.objects.create(name="Mock Artist")


@pytest.fixture
def user_record(user, artist, db):
    record = UserRecord.objects.create(
        user=user,
        title="Mock Album",
        year="2020",
        cover_image="http://cover.jpg",
        styles="Rock, Indie",
        added_at=timezone.now(),
    )
    record.artists.add(artist)
    return record


@pytest.mark.django_db
def test_top_records_added(client, user_record):
    url = reverse("top_records") + "?type=added"
    response = client.get(url)
    assert response.status_code == 200
    assert "stats/top_records.html" in [t.name for t in response.templates]
    assert "Mock Album" in response.content.decode()


@pytest.mark.django_db
def test_top_records_wished(client, user):
    Wishlist.objects.create(user=user, discogs_master_id="67890")

    url = reverse("top_records") + "?type=wished"
    response = client.get(url)
    assert response.status_code == 200
    assert "stats/top_records.html" in [t.name for t in response.templates]
    assert "Top 10 Discos más deseados" in response.content.decode()


@pytest.mark.django_db
def test_statistics_view(client, user, user_record):
    client.force_login(user)
    url = reverse("statistics")
    response = client.get(url)
    assert response.status_code == 200
    assert "stats/statistics.html" in [t.name for t in response.templates]
    assert "Dashboard de Colección" in response.content.decode()


@pytest.mark.django_db
def test_statistics_view_with_filters(client, user, user_record):
    client.force_login(user)
    url = reverse("statistics") + "?start_date=2020-01-01&end_date=2025-01-01"
    response = client.get(url)
    assert response.status_code == 200
    assert "stats/statistics.html" in [t.name for t in response.templates]
    assert "Dashboard de Colección" in response.content.decode()
