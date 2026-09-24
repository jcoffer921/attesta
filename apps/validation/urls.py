from django.urls import path

from . import views

urlpatterns = [
    path('permits/<slug:permit_slug>/', views.permit_rules, name='permit_rules'),
    path('runs/<int:run_id>/', views.validation_results, name='validation_results'),
    path('runs/<int:run_id>/provenance/', views.provenance_timeline, name='provenance_timeline'),
]
