# Python imports
from typing import Optional

# Third Party Imports
from asgiref.sync import sync_to_async

# Django Imports
from django.db.models import QuerySet

# Strawberry Imports
from strawberry.exceptions import GraphQLError

# Module Imports
from plane.db.models import Issue
from plane.graphql.types.workitem import WorkItemMentionType

# Local Imports
from .workspace import _get_workspace


# constructing work item mention query
def workitem_mention_base_query(
    workspace_slug: str,
    work_item_id: str,
    user_id: Optional[str] = None,
) -> QuerySet:
    # validating workspace
    workspace = _get_workspace(workspace_slug=workspace_slug)
    workspace_id = workspace.id

    # base query for workitem
    base_query = Issue.objects.filter(workspace_id=workspace_id).select_related("project", "state", "type")

    if work_item_id:
        base_query = base_query.filter(id=work_item_id)

    return base_query

    # getting work item mention


def get_work_item_mention(
    user_id: str,
    workspace_slug: str,
    work_item_id: str,
) -> WorkItemMentionType:
    try:
        base_query = workitem_mention_base_query(
            user_id=user_id,
            workspace_slug=workspace_slug,
            work_item_id=work_item_id,
        )

        work_item_mention = base_query.first()

        if work_item_mention is None:
            message = "Work item mention not found"
            error_extensions = {"code": "NOT_FOUND", "statusCode": 404}
            raise GraphQLError(message, extensions=error_extensions)

        return work_item_mention
    except Issue.DoesNotExist:
        message = "Work item mention not found"
        error_extensions = {"code": "NOT_FOUND", "statusCode": 404}
        raise GraphQLError(message, extensions=error_extensions)
    except Exception as e:
        message = e.message if hasattr(e, "message") else "Error getting work item mention"
        error_extensions = (
            {"code": "SOMETHING_WENT_WRONG", "statusCode": 400} if not hasattr(e, "extensions") else e.extensions
        )
        raise GraphQLError(message, extensions=error_extensions)


# getting work item mention async
@sync_to_async
def get_work_item_mention_async(
    user_id: str,
    workspace_slug: str,
    work_item_id: str,
) -> WorkItemMentionType:
    return get_work_item_mention(
        user_id=user_id,
        workspace_slug=workspace_slug,
        work_item_id=work_item_id,
    )
