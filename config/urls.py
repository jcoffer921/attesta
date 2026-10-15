"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from apps.reports import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('validation/', include('apps.validation.urls')),
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('app/dashboard/', views.dashboard, name='dashboard'),
    path('app/requirements/', views.requirements, name='requirements'),
    path('app/evidence/', views.evidence, name='evidence'),
    path('app/evidence/<int:evidence_id>/download/', views.evidence_download, name='evidence_download'),
    path('app/ai-review/', views.ai_review, name='ai_review'),
    path('app/ai-review/<int:evidence_id>/status/', views.ai_review_status, name='ai_review_status'),
    path('app/reports/', views.reports, name='reports'),
    path('app/audit-trail/', views.audit_trail, name='audit_trail'),
    path('app/settings/', views.settings_view, name='settings'),
    path('executive/', views.executive, name='executive'),
]
