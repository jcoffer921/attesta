from django.db import models


class ValidationRun(models.Model):
    """One invocation of the Stage 1 Racket engine's `run` command.

    Parent of both provenance (pipeline normalization) and results (permit
    evaluation), since a single CLI call does both. permit/pipeline slugs
    plus the SHA-256 of the definition files actually used at run time are
    stored so a given result can later be proven to come from a specific,
    unchanged rule definition -- permit files will change over time.
    """

    STATUS_CHOICES = [
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    permit_slug = models.CharField(max_length=100)
    pipeline_slug = models.CharField(max_length=100)
    permit_file_sha256 = models.CharField(max_length=64, blank=True)
    pipeline_file_sha256 = models.CharField(max_length=64, blank=True)
    period = models.CharField(max_length=7, null=True, blank=True)  # "YYYY-MM"

    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    schema_version = models.IntegerField(null=True, blank=True)  # what the engine actually returned
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ValidationRun({self.permit_slug}, {self.pipeline_slug}, {self.status})"


class LimitResult(models.Model):
    """One evidence trace for a single permit limit clause, verbatim from the engine."""

    run = models.ForeignKey(ValidationRun, related_name="results", on_delete=models.CASCADE)
    outfall = models.IntegerField()
    parameter = models.CharField(max_length=64)
    clause = models.CharField(max_length=32)
    sample_ids = models.JSONField()
    sample_values = models.JSONField()
    computed_value = models.CharField(max_length=64)
    threshold = models.CharField(max_length=64)
    comparison = models.CharField(max_length=64)
    status = models.CharField(max_length=16)  # verbatim from the engine; never recomputed or rewritten here
    reason = models.TextField()

    # Populated only by apps.ai_assist.services.explain_result, after the run
    # is already committed. Gemini interprets; it never writes a status.
    gemini_explanation = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"LimitResult({self.parameter}, {self.clause}, {self.status})"


class ProvenanceEntry(models.Model):
    """One normalization-step log entry for one record, verbatim from the engine."""

    run = models.ForeignKey(ValidationRun, related_name="provenance_entries", on_delete=models.CASCADE)
    step = models.CharField(max_length=32)
    record_id = models.CharField(max_length=64)
    before = models.JSONField()
    after = models.JSONField()
    note = models.TextField()


class RejectionEntry(models.Model):
    """One record that a pipeline step could not apply to, verbatim from the engine."""

    run = models.ForeignKey(ValidationRun, related_name="rejection_entries", on_delete=models.CASCADE)
    step = models.CharField(max_length=32)
    record_id = models.CharField(max_length=64)
    reason = models.TextField()
