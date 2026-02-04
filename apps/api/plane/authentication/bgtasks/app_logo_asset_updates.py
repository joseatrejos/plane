from celery import shared_task

@shared_task
def app_logo_asset_updates(application_id: str):
    from plane.authentication.models import Application, WorkspaceAppInstallation
    from plane.authentication.utils.oauth_utils import create_bot_user_avatar_asset

    all_workspace_installations = WorkspaceAppInstallation.objects.filter(
        application_id=application_id, deleted_at__isnull=True
    )

    application = Application.objects.get(id=application_id)

    for installation in all_workspace_installations:
        # creating new avatar for each app bot with new logo
        if installation.app_bot:
            installation.app_bot.avatar_asset = create_bot_user_avatar_asset(
                application.logo_asset, installation.app_bot
            )
            installation.app_bot.save()
