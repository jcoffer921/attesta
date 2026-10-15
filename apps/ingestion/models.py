from pathlib import Path

from django.conf import settings
from django.db import models


class Evidence(models.Model):
    class ReviewStatus(models.TextChoices):
        UPLOADED = "uploaded", "Ready for review"
        IN_REVIEW = "in_review", "In review"
        STOPPED = "stopped", "Review stopped"
        REVIEWED = "reviewed", "Reviewed"
        ERROR = "error", "Review error"

    organization = models.ForeignKey(
        "facilities.Organization",
        on_delete=models.CASCADE,
        related_name="evidence",
        null=True,
        blank=True,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_evidence",
    )
    file = models.FileField(upload_to="evidence/%Y/%m/")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255, blank=True)
    size = models.PositiveBigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.UPLOADED,
    )
    review_started_at = models.DateTimeField(null=True, blank=True)
    review_started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="started_evidence_reviews",
        null=True,
        blank=True,
    )
    review_stopped_at = models.DateTimeField(null=True, blank=True)
    review_stopped_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stopped_evidence_reviews",
        null=True,
        blank=True,
    )

    # Incremented on every start/stop so a finished background job can tell
    # whether it is still the current run before writing its result.
    review_run = models.PositiveIntegerField(default=0)
    review_completed_at = models.DateTimeField(null=True, blank=True)
    review_result = models.JSONField(null=True, blank=True)
    review_error = models.TextField(blank=True)
    # Current step while in review: one of claude_review.REVIEW_STEPS keys.
    review_stage = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["-uploaded_at", "-pk"]

    def __str__(self):
        return self.original_name

    @property
    def extension(self):
        return Path(self.original_name).suffix.removeprefix(".").upper() or "FILE"
