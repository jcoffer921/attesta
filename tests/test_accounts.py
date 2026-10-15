import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.facilities.models import Organization


@pytest.mark.django_db
def test_org_role_requires_organization():
    user = User(username="org-user", role=User.Role.ORG)
    with pytest.raises(ValidationError):
        user.full_clean()


@pytest.mark.django_db
def test_admin_role_rejects_organization():
    org = Organization.objects.create(name="Acme Water", slug="acme-water")
    user = User(username="admin-user", role=User.Role.ADMIN, organization=org)
    with pytest.raises(ValidationError):
        user.full_clean()


@pytest.mark.django_db
def test_org_role_with_organization_is_valid():
    org = Organization.objects.create(name="Acme Water", slug="acme-water")
    user = User(username="org-user", role=User.Role.ORG, organization=org)
    user.set_password("correct horse battery staple")
    user.full_clean()
    user.save()
    assert user.is_org_role
    assert not user.is_admin_role


@pytest.mark.django_db
def test_admin_role_without_organization_is_valid():
    user = User(username="admin-user", role=User.Role.ADMIN)
    user.set_password("correct horse battery staple")
    user.full_clean()
    user.save()
    assert user.is_admin_role
