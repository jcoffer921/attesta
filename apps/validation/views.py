from collections import defaultdict
from fractions import Fraction

from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.validation.models import ValidationRun
from apps.validation.services import EngineError, InvalidSlugError, describe_permit

# Status -> CSS badge class. Fixed mapping from the engine's own status
# string only -- never computed or restyled from AI text.
STATUS_BADGE_CLASSES = {
    "pass": "badge success",
    "exceedance": "badge danger",
    "missing-data": "badge warning",
    "unit-error": "badge unit-error",
    "report-only": "badge info",
}


def badge_class_for(status):
    return STATUS_BADGE_CLASSES.get(status, "badge neutral")


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
            .filter(permit_slug=run.permit_slug, status='success',
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


def validation_results(request, run_id):
    """One row per limit result, status badge from the stored engine status
    only, and the full trace shown expanded by default (not hidden behind
    the AI explanation). A run that already failed (persisted by
    services.run_validation) shows a clear error banner instead of an empty
    table -- this is historical data already in the database, not a live
    engine call, so it renders normally with a 200 and the stored error
    fields.
    """
    run = get_object_or_404(ValidationRun, pk=run_id)
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


def provenance_timeline(request, run_id):
    """Ordered pipeline steps per record, with any rejection appended at the
    point the record stopped progressing -- never silently dropped from the
    view either.
    """
    run = get_object_or_404(ValidationRun, pk=run_id)

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
