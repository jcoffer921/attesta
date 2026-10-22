from django.urls import path

from . import views

urlpatterns = [
    path('permits/<slug:permit_slug>/', views.permit_rules, name='permit_rules'),
    path('runs/', views.validation_run_list, name='validation_run_list'),
    path('runs/new/', views.validation_new, name='validation_new'),
    path('runs/<int:run_id>/', views.validation_results, name='validation_results'),
    path('runs/<int:run_id>/provenance/', views.provenance_timeline, name='provenance_timeline'),
    path('results/<int:result_id>/explain/', views.explain_limit_result, name='explain_limit_result'),
]
