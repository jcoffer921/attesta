import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.facilities.models import Organization

VALID_PAYLOAD = {
    'full_name': 'Jamie Rivers',
    'email': 'jamie@newco.test',
    'organization_name': 'Newco Water Treatment',
    'password': 'a-very-strong-passphrase',
    'password_confirm': 'a-very-strong-passphrase',
}


@pytest.mark.django_db
def test_signup_page_renders(client):
    response = client.get(reverse('signup'))
    assert response.status_code == 200
    assert 'Create your account' in response.content.decode()


@pytest.mark.django_db
def test_signup_creates_org_and_user_then_logs_in(client):
    response = client.post(reverse('signup'), VALID_PAYLOAD)

    assert response.status_code == 302
    assert response.url == reverse('dashboard')

    user = User.objects.get(username='jamie@newco.test')
    assert user.is_org_role
    assert user.organization.name == 'Newco Water Treatment'
    assert user.organization.slug == 'newco-water-treatment'
    assert user.check_password(VALID_PAYLOAD['password'])

    dashboard_response = client.get(reverse('dashboard'))
    assert dashboard_response.status_code == 200


@pytest.mark.django_db
def test_signup_rejects_mismatched_passwords(client):
    payload = dict(VALID_PAYLOAD, password_confirm='different')
    response = client.post(reverse('signup'), payload)

    assert response.status_code == 200
    assert 'Passwords do not match' in response.content.decode()
    assert not User.objects.filter(username='jamie@newco.test').exists()


@pytest.mark.django_db
def test_signup_rejects_duplicate_email(client):
    Organization.objects.create(name='Other Co', slug='other-co')
    User.objects.create_user(username='jamie@newco.test', email='jamie@newco.test', password='x')

    response = client.post(reverse('signup'), VALID_PAYLOAD)

    assert response.status_code == 200
    assert 'already exists' in response.content.decode()


@pytest.mark.django_db
def test_signup_rejects_duplicate_organization_name():
    from django.test import Client

    Organization.objects.create(name='Newco Water Treatment', slug='newco-water-treatment')
    client = Client()

    response = client.post(reverse('signup'), VALID_PAYLOAD)

    assert response.status_code == 200
    assert "already exists" in response.content.decode()
    assert not User.objects.filter(username='jamie@newco.test').exists()


@pytest.mark.django_db
def test_signup_rejects_weak_password(client):
    payload = dict(VALID_PAYLOAD, password='password', password_confirm='password')
    response = client.post(reverse('signup'), payload)

    assert response.status_code == 200
    assert not User.objects.filter(username='jamie@newco.test').exists()


def test_authenticated_user_visiting_signup_is_redirected(org_client):
    response = org_client.get(reverse('signup'))
    assert response.status_code == 302
    assert response.url == reverse('dashboard')
