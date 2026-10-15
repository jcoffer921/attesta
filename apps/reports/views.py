from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.facilities.models import Organization
from apps.ingestion import claude_review, review_jobs
from apps.ingestion.models import Evidence


ALLOWED_EVIDENCE_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"}
MAX_EVIDENCE_SIZE = 25 * 1024 * 1024


def home(request):
    return redirect('dashboard')


def _page(request, template, active, title, executive=False):
    return render(request, template, {
        'active': active,
        'page_title': title,
        'executive_shell': executive,
    })


def _default_redirect_for(user):
    return 'executive' if user.is_admin_role else 'dashboard'


def _authenticate_by_username_or_email(identifier, password):
    User = get_user_model()
    user = authenticate(username=identifier, password=password)
    if user is not None:
        return user
    try:
        candidate = User.objects.get(email__iexact=identifier)
    except (User.DoesNotExist, User.MultipleObjectsReturned):
        return None
    return authenticate(username=candidate.get_username(), password=password)


def login_view(request):
    if request.user.is_authenticated:
        return redirect(_default_redirect_for(request.user))

    error = None
    submitted_email = ''
    if request.method == 'POST':
        submitted_email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = _authenticate_by_username_or_email(submitted_email, password)
        if user is not None:
            auth_login(request, user)
            if request.POST.get('remember'):
                request.session.set_expiry(None)
            else:
                request.session.set_expiry(0)
            return redirect(_default_redirect_for(user))
        error = 'Invalid email or password.'

    return render(request, 'login.html', {
        'page_title': 'Sign in',
        'error': error,
        'submitted_email': submitted_email,
    })


def signup_view(request):
    if request.user.is_authenticated:
        return redirect(_default_redirect_for(request.user))

    User = get_user_model()
    error = None
    form = {}
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        organization_name = request.POST.get('organization_name', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        form = {'full_name': full_name, 'email': email, 'organization_name': organization_name}

        if not all([full_name, email, organization_name, password, password_confirm]):
            error = 'All fields are required.'
        elif password != password_confirm:
            error = 'Passwords do not match.'
        elif User.objects.filter(username__iexact=email).exists():
            error = 'An account with this email already exists.'
        elif Organization.objects.filter(slug=slugify(organization_name)).exists():
            error = "An organization with this name already exists. Ask that organization's admin for an invite."
        else:
            try:
                validate_password(password)
            except ValidationError as exc:
                error = ' '.join(exc.messages)

        if error is None:
            first_name, _, last_name = full_name.partition(' ')
            with transaction.atomic():
                org = Organization.objects.create(name=organization_name, slug=slugify(organization_name))
                user = User(
                    username=email,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role=User.Role.ORG,
                    organization=org,
                )
                user.set_password(password)
                user.save()
            auth_login(request, user)
            return redirect(_default_redirect_for(user))

    return render(request, 'signup.html', {
        'page_title': 'Create account',
        'error': error,
        'form': form,
    })


def logout_view(request):
    auth_logout(request)
    return redirect('login')


@login_required(login_url='login')
def dashboard(request):
    return _page(request, 'pages/dashboard.html', 'dashboard', 'Compliance Workspace')


@login_required(login_url='login')
def requirements(request):
    return _page(request, 'pages/requirements.html', 'requirements', 'Requirements')


@login_required(login_url='login')
def evidence(request):
    error = None
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    if request.method == "POST":
        files = request.FILES.getlist("files")
        if not files:
            error = "Choose at least one file to upload."
        else:
            for uploaded_file in files:
                extension = Path(uploaded_file.name).suffix.lower()
                if extension not in ALLOWED_EVIDENCE_EXTENSIONS:
                    error = f"{uploaded_file.name} is not a supported file type."
                    break
                if uploaded_file.size > MAX_EVIDENCE_SIZE:
                    error = f"{uploaded_file.name} is larger than 25 MB."
                    break

        if error is not None and is_ajax:
            return JsonResponse({"error": error}, status=400)

        if error is None:
            created = [
                Evidence.objects.create(
                    organization=request.user.organization,
                    uploaded_by=request.user,
                    file=uploaded_file,
                    original_name=Path(uploaded_file.name).name[:255],
                    content_type=uploaded_file.content_type or "",
                    size=uploaded_file.size,
                )
                for uploaded_file in files
            ]
            if is_ajax:
                primary = created[0]
                return JsonResponse({
                    "message": f"{len(created)} file{'s' if len(created) != 1 else ''} uploaded successfully.",
                    "evidence_id": primary.pk,
                    "filename": primary.original_name,
                    "file_type": primary.extension,
                    "size": primary.size,
                    "size_display": f"{primary.size / 1024:.1f} KB" if primary.size < 1024 * 1024 else f"{primary.size / 1024 / 1024:.1f} MB",
                    "review_url": f"{reverse('ai_review')}?evidence={primary.pk}&uploaded=1",
                    "rows_html": "".join(
                        render_to_string("partials/evidence_row.html", {"item": item}) for item in created
                    ),
                })
            return redirect(f"{reverse('evidence')}?uploaded={created[0].pk}")

    evidence_items = _visible_evidence(request.user)
    uploaded_evidence = None
    uploaded_id = request.GET.get("uploaded")
    if uploaded_id:
        uploaded_evidence = evidence_items.filter(pk=uploaded_id).first()

    return render(request, "pages/evidence.html", {
        "active": "evidence",
        "page_title": "Evidence",
        "evidence_items": evidence_items,
        "uploaded_evidence": uploaded_evidence,
        "upload_error": error,
    })


@login_required(login_url='login')
def ai_review(request):
    evidence_items = _visible_evidence(request.user)
    selected = None
    evidence_id = request.POST.get("evidence_id") if request.method == "POST" else request.GET.get("evidence")
    if evidence_id:
        selected = get_object_or_404(evidence_items, pk=evidence_id)

    if request.method == "POST":
        if selected is None:
            return redirect("ai_review")
        action = request.POST.get("action", "start")
        if action == "stop":
            # Bumping review_run makes any in-flight Claude result stale.
            stopped = Evidence.objects.filter(
                pk=selected.pk, review_status=Evidence.ReviewStatus.IN_REVIEW,
            ).update(
                review_status=Evidence.ReviewStatus.STOPPED,
                review_stopped_at=timezone.now(),
                review_stopped_by=request.user,
                review_run=F("review_run") + 1,
                review_stage="",
            )
            selected.refresh_from_db()
        else:
            Evidence.objects.filter(pk=selected.pk).update(
                review_status=Evidence.ReviewStatus.IN_REVIEW,
                review_started_at=timezone.now(),
                review_started_by=request.user,
                review_stopped_at=None,
                review_stopped_by=None,
                review_completed_at=None,
                review_result=None,
                review_error="",
                review_stage="reading",
                review_run=F("review_run") + 1,
            )
            selected.refresh_from_db()
            review_jobs.enqueue(selected.pk, selected.review_run)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(_review_status_payload(selected))
        event = "stopped" if action == "stop" else "started"
        return redirect(f"{reverse('ai_review')}?evidence={selected.pk}&{event}=1")

    if selected is not None:
        _expire_stale_review(selected)

    return render(request, "pages/ai_review.html", {
        "active": "ai_review",
        "page_title": "AI Review",
        "evidence_items": evidence_items,
        "selected_evidence": selected,
        "just_uploaded": request.GET.get("uploaded") == "1",
        "just_started": request.GET.get("started") == "1",
        "just_stopped": request.GET.get("stopped") == "1",
        "review_result": selected.review_result if selected is not None else None,
        "findings_count": _findings_count(selected.review_result if selected is not None else None),
        "review_steps": [label for _, label in claude_review.REVIEW_STEPS],
        "review_step": _review_status_payload(selected)["step"] if selected is not None else 0,
    })


def _findings_count(result):
    if not result:
        return 0
    return sum(len(result.get(key) or []) for key in ("key_criteria", "partial_matches", "potential_gaps"))


def _expire_stale_review(item):
    """Fail a review that has had no result for too long so it can be restarted."""
    if item.review_status != Evidence.ReviewStatus.IN_REVIEW or item.review_started_at is None:
        return
    age = (timezone.now() - item.review_started_at).total_seconds()
    if age <= settings.REVIEW_STALE_SECONDS:
        return
    message = "The review timed out before Claude returned a result. Please restart it."
    updated = Evidence.objects.filter(
        pk=item.pk, review_run=item.review_run, review_status=Evidence.ReviewStatus.IN_REVIEW,
    ).update(review_status=Evidence.ReviewStatus.ERROR, review_error=message)
    if updated:
        item.review_status = Evidence.ReviewStatus.ERROR
        item.review_error = message


def _review_status_payload(item):
    status_details = {
        Evidence.ReviewStatus.UPLOADED: ("Ready to begin", 0, "Select Begin Review to start analysis."),
        Evidence.ReviewStatus.IN_REVIEW: ("Review in progress", 35, "Claude is analyzing this document. This usually takes under a minute."),
        Evidence.ReviewStatus.STOPPED: ("Review stopped", 35, "Processing has stopped. Resume when you are ready to continue."),
        Evidence.ReviewStatus.REVIEWED: ("Review complete", 100, "Analysis is complete and ready for human verification."),
        Evidence.ReviewStatus.ERROR: ("Review needs attention", 100, "The review could not be completed. Restart it to try again."),
    }
    label, progress, detail = status_details[item.review_status]
    if item.review_status == Evidence.ReviewStatus.ERROR and item.review_error:
        detail = f"{item.review_error} Restart the review to try again."
    step_keys = [key for key, _ in claude_review.REVIEW_STEPS]
    step = step_keys.index(item.review_stage) if item.review_stage in step_keys else 0
    return {
        "evidence_id": item.pk,
        "step": step,
        "steps": [label for _, label in claude_review.REVIEW_STEPS],
        "status": item.review_status,
        "status_label": item.get_review_status_display(),
        "stage": label,
        "progress": progress,
        "detail": detail,
        "started_at": item.review_started_at.isoformat() if item.review_started_at else None,
        "status_url": reverse("ai_review_status", args=[item.pk]),
    }


@login_required(login_url='login')
def ai_review_status(request, evidence_id):
    item = get_object_or_404(_visible_evidence(request.user), pk=evidence_id)
    _expire_stale_review(item)
    return JsonResponse(_review_status_payload(item))


def _visible_evidence(user):
    queryset = Evidence.objects.select_related("uploaded_by", "organization")
    if user.is_admin_role:
        return queryset
    return queryset.filter(organization=user.organization)


@login_required(login_url='login')
def evidence_download(request, evidence_id):
    item = get_object_or_404(_visible_evidence(request.user), pk=evidence_id)
    return FileResponse(item.file.open("rb"), as_attachment=True, filename=item.original_name)


@login_required(login_url='login')
def reports(request):
    return _page(request, 'pages/reports.html', 'reports', 'Reports')


@login_required(login_url='login')
def audit_trail(request):
    return _page(request, 'pages/audit.html', 'audit', 'Audit Trail')


@login_required(login_url='login')
def settings_view(request):
    return _page(request, 'pages/settings.html', 'settings', 'Settings')


@login_required(login_url='login')
@user_passes_test(lambda user: user.is_admin_role, login_url='dashboard')
def executive(request):
    return _page(request, 'pages/executive.html', 'executive', 'Executive Overview', True)
