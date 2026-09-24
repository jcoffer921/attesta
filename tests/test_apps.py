from django.apps import apps


def test_all_five_domain_apps_registered():
    expected = {
        'facilities',
        'ingestion',
        'validation',
        'reports',
        'ai_assist',
    }
    registered = {config.label for config in apps.get_app_configs()}
    assert expected <= registered
