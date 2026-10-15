import pytest
from django.urls import reverse


@pytest.mark.parametrize(
    ('name', 'text'),
    [
        ('dashboard', 'Compliance Workspace'),
        ('requirements', 'Manage, track, and fulfill'),
        ('evidence', 'Upload, manage, and organize'),
        ('ai_review', 'No document selected'),
        ('reports', 'Recent Generated Reports'),
        ('audit_trail', 'No audit events recorded yet'),
        ('settings', 'AI Preferences'),
    ],
)
def test_org_page_renders(org_client, name, text):
    response = org_client.get(reverse(name))
    assert response.status_code == 200
    assert text in response.content.decode()


def test_executive_page_renders_for_admin(admin_client):
    response = admin_client.get(reverse('executive'))
    assert response.status_code == 200
    assert 'Monthly Recurring Revenue' in response.content.decode()


def test_executive_page_redirects_org_user_to_dashboard(org_client):
    response = org_client.get(reverse('executive'))
    assert response.status_code == 302
    assert response.url == f"{reverse('dashboard')}?next={reverse('executive')}"


def test_login_page_renders(client):
    response = client.get(reverse('login'))
    assert response.status_code == 200
    assert 'Sign in to your account' in response.content.decode()


@pytest.mark.parametrize('name', ['dashboard', 'requirements', 'evidence', 'ai_review', 'reports', 'audit_trail', 'settings', 'executive'])
def test_app_pages_redirect_anonymous_users_to_login(client, name):
    response = client.get(reverse(name))
    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={reverse(name)}"


def test_root_redirects_to_dashboard(org_client):
    response = org_client.get('/')
    assert response.status_code == 302
    assert response.url == reverse('dashboard')


def test_shared_shell_and_interaction_assets(org_client):
    response = org_client.get(reverse('requirements'))
    html = response.content.decode()
    assert 'data-shell' in html
    assert 'data-sidebar-toggle' in html
    assert 'data-table-search' in html
    assert 'js/app.js' in html
