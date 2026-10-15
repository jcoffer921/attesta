from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        ORG = "org", "Organization"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ORG)
    organization = models.ForeignKey(
        "facilities.Organization",
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
        help_text="Required for org-role users; ignored for admins.",
    )

    def clean(self):
        super().clean()
        if self.role == self.Role.ORG and self.organization_id is None:
            raise ValidationError({"organization": "Org-role users must belong to an organization."})
        if self.role == self.Role.ADMIN and self.organization_id is not None:
            raise ValidationError({"organization": "Admin users must not belong to an organization."})

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_org_role(self):
        return self.role == self.Role.ORG
