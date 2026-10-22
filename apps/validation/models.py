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

    # Nullable only for runs created before tenant scoping existed; those are
    # visible to admins alone. run_validation requires an organization, so
    # every new run is scoped.
    organization = models.ForeignKey(
        "facilities.Organization",
        on_delete=models.CASCADE,
        related_name="validation_runs",
        null=True,
        blank=True,
    )
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
    # is already committed. Claude interprets; it never writes a status.
    explanation = models.TextField(null=True, blank=True)
    # Ids the explanation cited (prov:/rej:/cite:) and the citation-map
    # version they were verified against. Written with explanation.
    explanation_refs = models.JSONField(null=True, blank=True)

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


class LabRecord(models.Model):
    """One raw lab row exactly as sent to the engine, kept for every run
    (successful or failed) so the input is never lost.
    """

    organization = models.ForeignKey(
        "facilities.Organization", on_delete=models.CASCADE, related_name="lab_records",
    )
    run = models.ForeignKey(ValidationRun, related_name="lab_records", on_delete=models.CASCADE)
    # 1-based data row in the source CSV.
    row_number = models.PositiveIntegerField()
    record_id = models.CharField(max_length=64)
    data = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "record_id"], name="unique_lab_record_per_run"),
        ]

    def __str__(self):
        return f"LabRecord({self.record_id}, row {self.row_number})"
