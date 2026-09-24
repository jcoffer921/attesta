import pytest
from django.urls import reverse


@pytest.mark.parametrize(
    ('name', 'text'),
    [
        ('login', 'Sign in to your account'),
        ('dashboard', 'Compliance Workspace'),
        ('requirements', 'Manage, track, and fulfill'),
        ('evidence', 'Upload, manage, and organize'),
        ('ai_review', 'Human review is required'),
        ('reports', 'Recent Generated Reports'),
        ('audit_trail', 'Audit Integrity'),
        ('settings', 'AI Preferences'),
        ('executive', 'Monthly Recurring Revenue'),
    ],
)
def test_product_page_renders(client, name, text):
    response = client.get(reverse(name))
    assert response.status_code == 200
    assert text in response.content.decode()


def test_root_redirects_to_dashboard(client):
    response = client.get('/')
    assert response.status_code == 302
    assert response.url == reverse('dashboard')


def test_shared_shell_and_interaction_assets(client):
    response = client.get(reverse('requirements'))
    html = response.content.decode()
    assert 'data-shell' in html
    assert 'data-sidebar-toggle' in html
    assert 'data-detail="requirement-drawer"' in html
    assert 'js/app.js' in html
