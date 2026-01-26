from celery import shared_task
import logging

@shared_task
def app_delete_updates(application_id: str):
    """
    This function deletes all app installations for an application.
    """
    from plane.authentication.models import Application, WorkspaceAppInstallation

    application = Application.objects.get(id=application_id)
    if not application:
        logging.getLogger("plane.worker").info(f"Application {application_id} not found")
        return
    app_installations = WorkspaceAppInstallation.objects.filter(
        application_id=application_id,
    )
    for app_installation in app_installations:
        app_installation.delete()
    return