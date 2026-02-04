# Third Party imports
from celery import shared_task

# Module imports
from plane.utils.notifications import NotificationContext
from plane.utils.exception_logger import log_exception


@shared_task
def process_teamspace_notifications(
    teamspace_id,
    workspace_id,
    actor_id,
    activities_data,
    requested_data=None,
    current_instance=None,
    subscriber=False,
    notification_type="",
):
    """
    Process notifications for teamspace activities.
    """
    try:
        # Import here to avoid circular imports
        from plane.utils.notifications import TeamspaceNotificationHandler

        # Let the handler normalize and parse activities
        activities = TeamspaceNotificationHandler.parse_activities(activities_data)

        # Create context
        context = NotificationContext(
            entity_id=teamspace_id,
            project_id=None,  # Teamspaces are not project-scoped
            workspace_id=workspace_id,
            actor_id=actor_id,
            activities=activities,
            requested_data=requested_data,
            current_instance=current_instance,
            subscriber=subscriber,
            notification_type=notification_type,
        )

        # Process notifications
        handler = TeamspaceNotificationHandler(context)
        payload = handler.process()

        return {
            "success": True,
            "in_app_count": len(payload.in_app_notifications),
            "email_count": len(payload.email_logs),
        }
    except Exception as e:
        log_exception(e)
        return {"success": False, "error": str(e)}


@shared_task
def process_initiative_notifications(
    initiative_id,
    workspace_id,
    actor_id,
    activities_data,
    requested_data=None,
    current_instance=None,
    subscriber=False,
    notification_type="",
):
    """
    Process notifications for initiative activities.
    """
    try:
        # Import here to avoid circular imports
        from plane.utils.notifications import InitiativeNotificationHandler

        # Let the handler normalize and parse activities
        activities = InitiativeNotificationHandler.parse_activities(activities_data)

        # Create context
        context = NotificationContext(
            entity_id=initiative_id,
            project_id=None,  # Initiatives are not project-scoped
            workspace_id=workspace_id,
            actor_id=actor_id,
            activities=activities,
            requested_data=requested_data,
            current_instance=current_instance,
            subscriber=subscriber,
            notification_type=notification_type,
        )

        # Process notifications
        handler = InitiativeNotificationHandler(context)
        payload = handler.process()

        return {
            "success": True,
            "in_app_count": len(payload.in_app_notifications),
            "email_count": len(payload.email_logs),
        }
    except Exception as e:
        log_exception(e)
        return {"success": False, "error": str(e)}