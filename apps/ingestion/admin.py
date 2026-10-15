from django.contrib import admin

from apps.ingestion.models import Evidence


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = (
        "original_name", "organization", "uploaded_by", "review_status", "uploaded_at",
    )
    list_filter = ("review_status", "organization", "content_type")
    search_fields = ("original_name", "uploaded_by__username", "organization__name")
    readonly_fields = (
        "size", "content_type", "uploaded_at", "review_started_at", "review_stopped_at",
    )
