import pytest
from django.urls import reverse
from django.test import Client


@pytest.mark.django_db
def test_search_view_no_query(client):
    url = reverse("search")
    response = client.get(url, {"q": ""})
    assert response.status_code == 200
    assert "records/search.html" in [t.name for t in response.templates]
    assert response.context["error"] == "Debes ingresar un término de búsqueda"


@pytest.mark.django_db
def test_search_view_with_mocked_results(client, monkeypatch):

    class DummyResponse:
        def json(self):
            return {
                "results": [
                    {"type": "artist", "id": 1, "title": "Mock Artist", "thumb": "http://img"},
                    {"type": "master", "title": "Mock Artist - Mock Album", "master_id": 123,
                     "cover_image": "http://cover", "year": "2000", "genre": ["Rock"], "style": ["Indie"],
                     "label": ["Mock Label"], "format": ["Vinyl"]},
                ],
                "pagination": {"pages": 1}
            }

    def fake_get(*args, **kwargs):
        return DummyResponse()

    monkeypatch.setattr("records.views.get_oauth_session", lambda: type("S", (), {"get": fake_get})())

    url = reverse("search")
    response = client.get(url, {"q": "Mock"})
    assert response.status_code == 200
    assert "records/search.html" in [t.name for t in response.templates]

    ctx = response.context
    assert ctx["query"] == "Mock"
    assert any(r["name"] == "Mock Artist" for r in ctx["results"] if r["type"] == "artist")
    assert any(r["title"] == "Mock Album" for r in ctx["results"] if r["type"] == "master")

@pytest.mark.django_db
def test_fetch_preview_url_success(client, monkeypatch):

    def fake_get(url):
        class DummyResponse:
            def json(self_inner):
                return {"preview": "http://example.com/preview.mp3"}
        return DummyResponse()

    monkeypatch.setattr("records.views.requests.get", fake_get)

    url = reverse("fetch_preview", args=[123])
    response = client.get(url)
    assert response.status_code == 200
    assert response.json()["preview"] == "http://example.com/preview.mp3"


@pytest.mark.django_db
def test_fetch_preview_url_failure(client, monkeypatch):
    def fake_get(url):
        raise Exception("Network error")

    monkeypatch.setattr("records.views.requests.get", fake_get)

    url = reverse("fetch_preview", args=[999])
    response = client.get(url)
    assert response.status_code == 500
    assert response.json()["preview"] is None


def test_track_position_key():
    from records.views import track_position_key

    assert track_position_key("A1") < track_position_key("A2")
    assert track_position_key("B1") > track_position_key("A10")
    assert track_position_key("") == (float("inf"), float("inf"))
