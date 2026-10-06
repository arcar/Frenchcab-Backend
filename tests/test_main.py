from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_route_test_renvoie_200():
    response = client.get("/test")

    assert response.status_code == 200
    assert response.json() == {"test": "la route fonctionne"}


def test_route_inconnue_renvoie_404():
    response = client.get("/route-inexistante")

    assert response.status_code == 404
