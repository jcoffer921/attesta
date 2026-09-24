from django.shortcuts import redirect, render


def home(request):
    return redirect('dashboard')


def _page(request, template, active, title, executive=False):
    return render(request, template, {
        'active': active,
        'page_title': title,
        'executive_shell': executive,
    })


def login_view(request):
    return render(request, 'login.html', {'page_title': 'Sign in'})


def dashboard(request):
    return _page(request, 'pages/dashboard.html', 'dashboard', 'Compliance Workspace')


def requirements(request):
    return _page(request, 'pages/requirements.html', 'requirements', 'Requirements')


def evidence(request):
    return _page(request, 'pages/evidence.html', 'evidence', 'Evidence')


def ai_review(request):
    return _page(request, 'pages/ai_review.html', 'ai_review', 'AI Review')


def reports(request):
    return _page(request, 'pages/reports.html', 'reports', 'Reports')


def audit_trail(request):
    return _page(request, 'pages/audit.html', 'audit', 'Audit Trail')


def settings_view(request):
    return _page(request, 'pages/settings.html', 'settings', 'Settings')


def executive(request):
    return _page(request, 'pages/executive.html', 'executive', 'Executive Overview', True)
