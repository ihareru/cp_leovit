
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_page(client):
    response = client.get(reverse("home"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_tickets_page(client):
    response = client.get(reverse("tickets:list"))
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    ["forms", "contacts", "access"],
)
def test_placeholder_pages(client, url_name):
    response = client.get(reverse(url_name))
    assert response.status_code == 200