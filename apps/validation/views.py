from collections import defaultdict
from fractions import Fraction

from django.contrib.auth.decorators import login_required
import re

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.ai_assist.services import ExplanationError, explain_result

from apps.validation.csv_import import LabCsvError, parse_lab_csv
from apps.validation.models import LimitResult, ValidationRun
from apps.validation.services import (
    EngineError,
    InvalidSlugError,
    available_permit_slugs,
    describe_permit,
    run_validation,
)

LAB_CSV_PIPELINE_SLUG = "lab-csv-import"
_PERIOD_RE = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")

# Status -> CSS badge class. Fixed mapping from the engine's own status
# string only -- never computed or restyled from AI text.
STATUS_BADGE_CLASSES = {
    "pass": "badge success",
    "exceedance": "badge danger",
    "review-required": "badge warning",
    "under-sampled": "badge warning",
    "missing-data": "badge warning",
    "unit-error": "badge unit-error",
    "report-only": "badge info",
}


def badge_class_for(status):
    return STATUS_BADGE_CLASSES.get(status, "badge neutral")


def _visible_runs(user):
    """Runs the user may see: all for admins, own organization's otherwise.
    Legacy runs with no organization match no org user.
    """
    if user.is_admin_role:
        return ValidationRun.objects.all()
    return ValidationRun.objects.filter(organization=user.organization)


@login_required(login_url='login')
def permit_rules(request, permit_slug):
    """Renders a permit's limits from the engine's `describe` JSON only.

    A bad or unknown slug is a client error (404, no subprocess call --
    services.describe_permit already validates the slug before ever
    touching Racket). A broken permit file, timeout, or malformed engine
    output is a server-side failure: render a friendly error state with a
    5xx status rather than a 200 that hides it. Only the error code and a
    generic message are shown -- never the raw engine message, which can
    contain filesystem paths.
    """
    try:
        permit = describe_permit(permit_slug=permit_slug)
    except InvalidSlugError:
        raise Http404("Unknown permit.")
    except EngineError as exc:
        return render(
            request,
            'pages/permit_rules.html',
            {
                'permit_slug': permit_slug,
                'error': {
                    'code': exc.code,
                    'message': "The rule engine could not describe this permit.",
                },
                'active': 'permit_rules',
                'page_title': f'Permit {permit_slug}',
            },
            status=502,
        )

    return render(
        request,
        'pages/permit_rules.html',
        {
            'permit_slug': permit_slug,
            'permit': permit,
            'active': 'permit_rules',
            'page_title': f"Permit {permit.get('permit_id', permit_slug)}",
        },
    )


def _to_float(value_str):
    try:
        return float(Fraction(value_str))
    except (ValueError, ZeroDivisionError):
        return None


def _monthly_avg_chart_series(run, results):
    """Historical monthly-avg computed values vs. threshold, per (outfall,
    parameter), across other runs sharing this run's permit. Display-only:
    never touches a stored status or value, just re-renders it as a float
    for Chart.js.
    """
    series = {}
    for result in results:
        if result.clause != 'monthly-avg' or result.status not in ('pass', 'exceedance'):
            continue
        key = (result.outfall, result.parameter)
        if key in series:
            continue
        history_qs = (
            ValidationRun.objects
            .filter(organization=run.organization, permit_slug=run.permit_slug, status='success',
                    results__outfall=result.outfall, results__parameter=result.parameter,
                    results__clause='monthly-avg')
            .exclude(period__isnull=True)
            .order_by('period')
            .prefetch_related('results')
        )
        points = []
        for historical_run in history_qs:
            for r in historical_run.results.all():
                if r.outfall == result.outfall and r.parameter == result.parameter and r.clause == 'monthly-avg':
                    value = _to_float(r.computed_value)
                    if value is not None:
                        points.append({'period': historical_run.period, 'value': value})
        if len(points) < 2:
            continue
        threshold = _to_float(result.threshold)
        series[f"{result.outfall}-{result.parameter}"] = {
            'outfall': result.outfall,
            'parameter': result.parameter,
            'points': points,
            'threshold': threshold,
        }
    return series


@login_required(login_url='login')
def validation_results(request, run_id):
    """One row per limit result, status badge from the stored engine status
    only, and the full trace shown expanded by default (not hidden behind
    the AI explanation). A run that already failed (persisted by
    services.run_validation) shows a clear error banner instead of an empty
    table -- this is historical data already in the database, not a live
    engine call, so it renders normally with a 200 and the stored error
    fields.
    """
    run = get_object_or_404(_visible_runs(request.user), pk=run_id)
    results = list(run.results.all().order_by('outfall', 'parameter', 'clause'))
    for result in results:
        result.badge_class = badge_class_for(result.status)
    chart_series = _monthly_avg_chart_series(run, results) if run.status == 'success' else {}

    return render(
        request,
        'pages/validation_results.html',
        {
            'run': run,
            'results': results,
            'chart_series': chart_series,
            'active': 'validation_results',
            'page_title': f'Validation results — {run.permit_slug}',
        },
    )


@login_required(login_url='login')
def provenance_timeline(request, run_id):
    """Ordered pipeline steps per record, with any rejection appended at the
    point the record stopped progressing -- never silently dropped from the
    view either.
    """
    run = get_object_or_404(_visible_runs(request.user), pk=run_id)

    by_record = defaultdict(lambda: {'steps': [], 'rejection': None})
    for entry in run.provenance_entries.all().order_by('id'):
        by_record[entry.record_id]['steps'].append(entry)
    for entry in run.rejection_entries.all().order_by('id'):
        by_record[entry.record_id]['rejection'] = entry

    timeline = [
        {'record_id': record_id, 'steps': data['steps'], 'rejection': data['rejection']}
        for record_id, data in sorted(by_record.items())
    ]

    return render(
        request,
        'pages/provenance_timeline.html',
        {
            'run': run,
            'timeline': timeline,
            'active': 'provenance_timeline',
            'page_title': f'Provenance — {run.permit_slug}',
        },
    )


@login_required(login_url='login')
def validation_run_list(request):
    runs = _visible_runs(request.user).order_by('-started_at', '-pk')
    return render(
        request,
        'pages/validation_run_list.html',
        {'runs': runs, 'active': 'validation_runs', 'page_title': 'Validation runs'},
    )


@login_required(login_url='login')
def validation_new(request):
    """Lab CSV + permit + period -> persisted ValidationRun.

    This view only moves the upload into the engine's record shape; the
    engine decides every status. Org users only: a run must belong to an
    organization.
    """
    organization = request.user.organization
    context = {
        'permit_slugs': available_permit_slugs(),
        'active': 'validation_runs',
        'page_title': 'New validation run',
        'org_only': organization is None,
        'selected_permit': request.POST.get('permit_slug', ''),
        'period': request.POST.get('period', ''),
    }
    if organization is None:
        return render(request, 'pages/validation_new.html', context,
                      status=403 if request.method == 'POST' else 200)
    if request.method != 'POST':
        return render(request, 'pages/validation_new.html', context)

    def invalid(message):
        return render(request, 'pages/validation_new.html', {**context, 'error': message}, status=400)

    permit_slug = request.POST.get('permit_slug', '')
    period = request.POST.get('period', '').strip()
    upload = request.FILES.get('csv_file')
    if permit_slug not in context['permit_slugs']:
        return invalid("Choose a permit from the list.")
    if not _PERIOD_RE.match(period):
        return invalid("Period must look like 2026-03 (YYYY-MM).")
    if upload is None:
        return invalid("Choose a CSV file to upload.")
    try:
        records, row_numbers = parse_lab_csv(upload.read())
    except LabCsvError as exc:
        return invalid(str(exc))

    try:
        run = run_validation(
            organization=organization,
            permit_slug=permit_slug,
            pipeline_slug=LAB_CSV_PIPELINE_SLUG,
            records=records,
            period=period,
            row_numbers=row_numbers,
        )
    except InvalidSlugError:
        return invalid("That permit could not be used.")
    except EngineError as exc:
        if exc.run is None:
            return invalid("The rule engine could not run. Try again.")
        return redirect('validation_results', run_id=exc.run.pk)
    return redirect('validation_results', run_id=run.pk)


@login_required(login_url='login')
@require_POST
def explain_limit_result(request, result_id):
    """Ask Claude to explain one stored result. explain_result writes only
    the explanation fields; the flash text is generic so raw Claude or
    filesystem text never reaches the page.
    """
    result = get_object_or_404(LimitResult.objects.filter(run__in=_visible_runs(request.user)), pk=result_id)
    try:
        explain_result(result.pk)
    except ExplanationError:
        messages.error(request, "An explanation could not be generated for this result. Try again later.")
    else:
        messages.success(request, "Explanation added.")
    return redirect('validation_results', run_id=result.run_id)
