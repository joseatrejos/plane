# Python Imports
from typing import List, Optional

# Third Party Imports
from asgiref.sync import sync_to_async

# Django Imports
from django.db.models import QuerySet

# Strawberry Imports
from strawberry.exceptions import GraphQLError

# Module Imports
from plane.db.models import PageLog
from plane.graphql.types.page import PageMentionEntityNameEnum, PageMentionType

# Local Imports
from .feature_flag import is_page_mention_feature_flagged
from ...project import _get_project
from ...workspace import _get_workspace


# constructing page log query
def page_log_base_query(
    user_id: str,
    workspace_slug: str,
    page_id: str,
    project_id: Optional[str] = None,
    entity_name: Optional[List[PageMentionEntityNameEnum]] = None,
    order_by: Optional[str] = "-created_at",
    mention_id: Optional[str] = None,
) -> QuerySet:
    # Feature Flag validation
    is_page_mention_feature_flagged(workspace_slug=workspace_slug, user_id=user_id)

    # base query for page mentions
    base_query = PageLog.objects.filter(workspace__slug=workspace_slug, page_id=page_id).prefetch_related(
        "page", "page__projects"
    )

    # validating workspace
    workspace = _get_workspace(workspace_slug=workspace_slug)
    workspace_slug = workspace.slug

    # validating project
    if project_id:
        _get_project(workspace_slug=workspace_slug, project_id=project_id)

    # entity type filter
    if entity_name:
        entity_names = [entity.value for entity in entity_name]
        base_query = base_query.filter(entity_name__in=entity_names)

    if mention_id:
        base_query = base_query.filter(id=mention_id)

    # Order by
    base_query = base_query.order_by(order_by)

    return base_query


# listing page mentions
def get_page_mentions(
    user_id: str,
    workspace_slug: str,
    page_id: str,
    project_id: Optional[str] = None,
    entity_name: Optional[List[PageMentionEntityNameEnum]] = None,
    order_by: Optional[str] = "-created_at",
) -> list[PageMentionType]:
    base_query = page_log_base_query(
        user_id=user_id,
        workspace_slug=workspace_slug,
        page_id=page_id,
        project_id=project_id,
        order_by=order_by,
        entity_name=entity_name,
    )

    page_mentions = base_query.all()

    return list(page_mentions)


# listing page mentions async
@sync_to_async
def get_page_mentions_async(
    user_id: str,
    workspace_slug: str,
    page_id: str,
    project_id: Optional[str] = None,
    entity_name: Optional[List[PageMentionEntityNameEnum]] = None,
    order_by: Optional[str] = "-created_at",
) -> list[PageMentionType]:
    return get_page_mentions(
        workspace_slug=workspace_slug,
        project_id=project_id,
        page_id=page_id,
        user_id=user_id,
        entity_name=entity_name,
        order_by=order_by,
    )


# getting page mention
def get_page_mention(
    user_id: str,
    workspace_slug: str,
    page_id: str,
    mention_id: str,
    project_id: Optional[str] = None,
) -> PageMentionType:
    try:
        base_query = page_log_base_query(
            user_id=user_id,
            workspace_slug=workspace_slug,
            page_id=page_id,
            project_id=project_id,
            mention_id=mention_id,
        )

        page_mention = base_query.first()

        if page_mention is None:
            message = "Page mention not found"
            error_extensions = {"code": "NOT_FOUND", "statusCode": 404}
            raise GraphQLError(message, extensions=error_extensions)

        return page_mention
    except PageLog.DoesNotExist:
        message = "Page mention not found"
        error_extensions = {"code": "NOT_FOUND", "statusCode": 404}
        raise GraphQLError(message, extensions=error_extensions)
    except Exception as e:
        message = e.message if hasattr(e, "message") else "Error getting page mention"
        error_extensions = (
            {"code": "SOMETHING_WENT_WRONG", "statusCode": 400} if not hasattr(e, "extensions") else e.extensions
        )
        raise GraphQLError(message, extensions=error_extensions)


# getting page mention async
@sync_to_async
def get_page_mention_async(
    user_id: str,
    workspace_slug: str,
    page_id: str,
    mention_id: str,
    project_id: Optional[str] = None,
) -> PageMentionType:
    return get_page_mention(
        user_id=user_id,
        workspace_slug=workspace_slug,
        page_id=page_id,
        mention_id=mention_id,
        project_id=project_id,
    )
