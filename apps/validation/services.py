"""Service layer that invokes the Stage 1 Racket rule engine and persists
its output.

The rule engine decides; this module only calls it, validates its JSON
contract, and stores the result exactly as returned -- it never recomputes
or overwrites a status.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess

from django.conf import settings
from django.db import transaction

from apps.validation.models import (
    LabRecord,
    LimitResult,
    ProvenanceEntry,
    RejectionEntry,
    ValidationRun,
)

EXPECTED_SCHEMA_VERSION = 3

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class EngineError(Exception):
    """Raised after the failing ValidationRun (if any) has already been persisted."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        # The persisted failed ValidationRun, when one was created.
        self.run = None
        super().__init__(f"{code}: {message}")


class InvalidSlugError(EngineError):
    """A permit/pipeline slug failed validation before any subprocess was run."""


def _resolve_definition_file(slug: str, subdir: str, label: str):
    """Resolve `slug` to a file under DSL_ROOT/subdir, refusing anything that
    would escape that directory (including via a symlink), mirroring -- as a
    second, independent check -- the same restriction the Racket CLI itself
    enforces on --permit/--pipeline.
    """
    if not _SLUG_RE.match(slug):
        raise InvalidSlugError(
            "invalid-slug",
            f"{label} slug {slug!r} does not match {_SLUG_RE.pattern}",
        )
    root = (settings.DSL_ROOT / subdir).resolve()
    candidate = (root / f"{slug}.rkt").resolve()
    if not candidate.is_relative_to(root):
        raise InvalidSlugError(
            "invalid-slug",
            f"{label} slug {slug!r} resolves outside {root}",
        )
    if not candidate.is_file():
        raise InvalidSlugError(
            "file-error",
            f"{label} definition not found: {candidate}",
        )
    return candidate


def _sha256_of(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lab_records(run, organization, records, row_numbers) -> list[LabRecord]:
    if not row_numbers:
        return []
    return [
        LabRecord(organization=organization, run=run, row_number=n, record_id=rec["id"], data=rec)
        for rec, n in zip(records, row_numbers)
    ]


def _fail(*, organization, permit_slug, pipeline_slug, period, code, message,
          permit_sha=None, pipeline_sha=None, schema_version=None,
          records=None, row_numbers=None) -> ValidationRun:
    """Persist a failed ValidationRun (plus its raw LabRecords, if any) with
    no result rows and raise EngineError carrying that run.
    """
    from django.utils import timezone

    with transaction.atomic():
        run = ValidationRun.objects.create(
            organization=organization,
            permit_slug=permit_slug,
            pipeline_slug=pipeline_slug,
            permit_file_sha256=permit_sha or "",
            pipeline_file_sha256=pipeline_sha or "",
            period=period,
            status="failed",
            schema_version=schema_version,
            error_code=code,
            error_message=message,
            finished_at=timezone.now(),
        )
        LabRecord.objects.bulk_create(_lab_records(run, organization, records, row_numbers))
    exc = EngineError(code, message)
    exc.run = run
    raise exc


def available_permit_slugs() -> list[str]:
    """Slugs of the permit definitions on disk; no subprocess."""
    return sorted(p.stem for p in (settings.DSL_ROOT / "permit/permits").glob("*.rkt"))


def run_validation(*, organization, permit_slug: str, pipeline_slug: str, records: list,
                   period: str | None = None, row_numbers: list[int] | None = None) -> ValidationRun:
    """Invoke `racket dsl/main.rkt run`, validate its JSON contract, and
    persist the outcome atomically.

    On success: one ValidationRun(status="success") plus its LimitResults,
    ProvenanceEntries and RejectionEntries, all in one transaction.

    On any failure (nonzero exit, timeout, malformed JSON, wrong
    schema_version): one ValidationRun(status="failed") with no result rows,
    and EngineError (with the run on `exc.run`) is raised. When
    `row_numbers` is given, the raw LabRecords are stored with the run in
    both cases.
    """
    if row_numbers is not None and len(row_numbers) != len(records):
        raise ValueError("row_numbers must be the same length as records")
    permit_path = _resolve_definition_file(permit_slug, "permit/permits", "--permit")
    pipeline_path = _resolve_definition_file(pipeline_slug, "pipeline/pipelines", "--pipeline")
    permit_sha = _sha256_of(permit_path)
    pipeline_sha = _sha256_of(pipeline_path)

    args = [
        str(settings.RACKET_EXECUTABLE),
        str(settings.DSL_ROOT / "main.rkt"),
        "run",
        "--permit", str(permit_path),
        "--pipeline", str(pipeline_path),
    ]
    if period:
        args += ["--period", period]

    stdin_payload = json.dumps({"schema_version": EXPECTED_SCHEMA_VERSION, "records": records}).encode("utf-8")

    common_fail_kwargs = dict(
        organization=organization, permit_slug=permit_slug, pipeline_slug=pipeline_slug, period=period,
        permit_sha=permit_sha, pipeline_sha=pipeline_sha,
        records=records, row_numbers=row_numbers,
    )

    try:
        proc = subprocess.run(
            args,
            input=stdin_payload,
            capture_output=True,
            timeout=settings.RACKET_TIMEOUT_SECONDS,
            check=False,
        )
    except OSError as exc:
        # Missing/unlaunchable RACKET_EXECUTABLE: keep the run and raw input.
        _fail(code="engine-unavailable",
              message=f"could not start the rule engine: {type(exc).__name__}",
              **common_fail_kwargs)
    except subprocess.TimeoutExpired:
        _fail(code="timeout",
              message=f"racket did not exit within {settings.RACKET_TIMEOUT_SECONDS}s",
              **common_fail_kwargs)

    stdout_text = proc.stdout.decode("utf-8", errors="replace")

    if proc.returncode != 0:
        try:
            payload = json.loads(stdout_text)
            error = payload["error"]
            code, message = error["code"], error["message"]
        except (json.JSONDecodeError, KeyError, TypeError):
            stderr_text = proc.stderr.decode("utf-8", errors="replace")
            code, message = "engine-crash", (stdout_text + stderr_text)[:2000]
        _fail(code=code, message=message, **common_fail_kwargs)

    try:
        payload = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        _fail(code="invalid-json", message=f"engine returned malformed JSON: {exc}", **common_fail_kwargs)

    schema_version = payload.get("schema_version")
    if schema_version != EXPECTED_SCHEMA_VERSION:
        _fail(code="unexpected-schema-version",
              message=f"expected schema_version {EXPECTED_SCHEMA_VERSION}, got {schema_version!r}",
              schema_version=schema_version, **common_fail_kwargs)

    from django.utils import timezone

    with transaction.atomic():
        run = ValidationRun.objects.create(
            organization=organization,
            permit_slug=permit_slug,
            pipeline_slug=pipeline_slug,
            permit_file_sha256=permit_sha,
            pipeline_file_sha256=pipeline_sha,
            period=period,
            status="success",
            schema_version=schema_version,
            finished_at=timezone.now(),
        )
        LimitResult.objects.bulk_create([
            LimitResult(
                run=run,
                outfall=r["outfall"],
                parameter=r["parameter"],
                clause=r["clause"],
                sample_ids=r["sample_ids"],
                sample_values=r["sample_values"],
                computed_value=r["computed_value"],
                threshold=r["threshold"],
                comparison=r["comparison"],
                status=r["status"],
                reason=r["reason"],
            )
            for r in payload["results"]
        ])
        ProvenanceEntry.objects.bulk_create([
            ProvenanceEntry(
                run=run,
                step=p["step"],
                record_id=p["record_id"],
                before=p["before"],
                after=p["after"],
                note=p["note"],
            )
            for p in payload["provenance"]
        ])
        RejectionEntry.objects.bulk_create([
            RejectionEntry(
                run=run,
                step=rej["step"],
                record_id=rej["record_id"],
                reason=rej["reason"],
            )
            for rej in payload["rejections"]
        ])
        LabRecord.objects.bulk_create(_lab_records(run, organization, records, row_numbers))

    return run


def describe_permit(*, permit_slug: str) -> dict:
    """Invoke `racket dsl/main.rkt describe`; validate schema_version; return
    the permit jsexpr. No persistence.
    """
    permit_path = _resolve_definition_file(permit_slug, "permit/permits", "--permit")

    args = [
        str(settings.RACKET_EXECUTABLE),
        str(settings.DSL_ROOT / "main.rkt"),
        "describe",
        "--permit", str(permit_path),
    ]

    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            timeout=settings.RACKET_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise EngineError("timeout", f"racket did not exit within {settings.RACKET_TIMEOUT_SECONDS}s")

    stdout_text = proc.stdout.decode("utf-8", errors="replace")

    if proc.returncode != 0:
        try:
            payload = json.loads(stdout_text)
            error = payload["error"]
            raise EngineError(error["code"], error["message"])
        except (json.JSONDecodeError, KeyError, TypeError):
            stderr_text = proc.stderr.decode("utf-8", errors="replace")
            raise EngineError("engine-crash", (stdout_text + stderr_text)[:2000])

    try:
        payload = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        raise EngineError("invalid-json", f"engine returned malformed JSON: {exc}")

    schema_version = payload.get("schema_version")
    if schema_version != EXPECTED_SCHEMA_VERSION:
        raise EngineError(
            "unexpected-schema-version",
            f"expected schema_version {EXPECTED_SCHEMA_VERSION}, got {schema_version!r}",
        )

    return payload["permit"]
