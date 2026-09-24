from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.validation.models import LimitResult, ProvenanceEntry, RejectionEntry, ValidationRun


class LimitResultInline(admin.TabularInline):
    model = LimitResult
    extra = 0
    can_delete = False
    fields = ("outfall", "parameter", "clause", "status", "computed_value", "threshold", "reason")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ValidationRun)
class ValidationRunAdmin(admin.ModelAdmin):
    """Read-only admin view of engine runs -- a working entry point to the
    results/provenance pages until a dedicated run-list page exists.
    """

    list_display = ("id", "permit_slug", "pipeline_slug", "period", "status", "started_at", "evidence_links")
    list_filter = ("status", "permit_slug", "pipeline_slug")
    ordering = ("-started_at",)
    inlines = [LimitResultInline]
    readonly_fields = [f.name for f in ValidationRun._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def evidence_links(self, obj):
        results_url = reverse("validation_results", args=[obj.pk])
        provenance_url = reverse("provenance_timeline", args=[obj.pk])
        permit_url = reverse("permit_rules", args=[obj.permit_slug])
        return format_html(
            '<a href="{}">Results</a> · <a href="{}">Provenance</a> · <a href="{}">Permit rules</a>',
            results_url, provenance_url, permit_url,
        )
    evidence_links.short_description = "Evidence pages"


@admin.register(ProvenanceEntry)
class ProvenanceEntryAdmin(admin.ModelAdmin):
    list_display = ("run", "record_id", "step", "note")
    list_filter = ("step",)

    def has_add_permission(self, request):
        return False


@admin.register(RejectionEntry)
class RejectionEntryAdmin(admin.ModelAdmin):
    list_display = ("run", "record_id", "step", "reason")

    def has_add_permission(self, request):
        return False
