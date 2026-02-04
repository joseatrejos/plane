# Python Imports
import copy
from typing import Optional

# Third-Party Imports
import strawberry
from asgiref.sync import sync_to_async

# Django Imports
from django.db.models import Exists, OuterRef, Q, Subquery
from django.utils import timezone

# Strawberry Imports
from strawberry.permission import PermissionExtension
from strawberry.scalars import JSON
from strawberry.types import Info

# Module Imports
from plane.db.models import (
    Issue,
    IssueAssignee,
    IssueSubscriber,
    IntakeIssue,
    Notification,
    Workspace,
    WorkspaceMember,
)
from plane.graphql.bgtasks.push_notifications.helper import notification_count
from plane.graphql.helpers.teamspace import project_member_filter_via_teamspaces_async
from plane.graphql.permissions.workspace import IsAuthenticated, WorkspaceBasePermission
from plane.graphql.types.notification import (
    NotificationCountBaseType,
    NotificationCountType,
    NotificationCountWorkspaceType,
    NotificationType,
)
from plane.graphql.types.paginator import PaginatorResponse
from plane.graphql.utils.paginator import query_paginate_async


@sync_to_async
def get_notification_count(user_id: str) -> NotificationCountBaseType:
    unread_notification_count = notification_count(
        user_id=user_id, workspace_slug=None, mentioned=False, combined=False
    )
    mentioned_notification_count = notification_count(
        user_id=user_id, workspace_slug=None, mentioned=True, combined=False
    )

    return NotificationCountBaseType(unread=unread_notification_count, mentioned=mentioned_notification_count)


@sync_to_async
def get_notification_count_by_workspaces(
    user_id: str,
) -> NotificationCountWorkspaceType:
    user_workspaces = Workspace.objects.filter(workspace_member__member=user_id, workspace_member__is_active=True)

    workspaces_notification_counts = []

    if user_workspaces.exists():
        for workspace in user_workspaces:
            workspace_id = str(workspace.id)
            workspace_slug = workspace.slug
            workspace_name = workspace.name

            unread_notification_count = notification_count(
                user_id=user_id,
                workspace_slug=workspace_slug,
                mentioned=False,
                combined=False,
            )
            mentioned_notification_count = notification_count(
                user_id=user_id,
                workspace_slug=workspace_slug,
                mentioned=True,
                combined=False,
            )

            workspace_notification_count = NotificationCountWorkspaceType(
                id=workspace_id,
                slug=workspace_slug,
                name=workspace_name,
                unread=unread_notification_count,
                mentioned=mentioned_notification_count,
            )
            workspaces_notification_counts.append(workspace_notification_count)

    return workspaces_notification_counts


@strawberry.type
class NotificationCountQuery:
    @strawberry.field(extensions=[PermissionExtension(permissions=[IsAuthenticated()])])
    async def notification_count(self, info: Info) -> NotificationCountType:
        user = info.context.user
        user_id = str(user.id)

        global_notification_count = await get_notification_count(user_id=user_id)
        workspaces_notification_counts = await get_notification_count_by_workspaces(user_id=user_id)

        return NotificationCountType(
            unread=global_notification_count.unread,
            mentioned=global_notification_count.mentioned,
            workspaces=workspaces_notification_counts,
        )


@strawberry.type
class NotificationQuery:
    @strawberry.field(extensions=[PermissionExtension(permissions=[WorkspaceBasePermission()])])
    async def notifications(
        self,
        info: Info,
        slug: str,
        type: Optional[JSON] = "all",
        snoozed: Optional[bool] = False,
        archived: Optional[bool] = False,
        mentioned: Optional[bool] = None,
        read: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> PaginatorResponse[NotificationType]:
        user = info.context.user
        user_id = str(user.id)

        # Teamspace Filter
        project_teamspace_filter = await project_member_filter_via_teamspaces_async(
            user_id=user_id, workspace_slug=slug
        )

        notification_queryset = (
            Notification.objects.filter(project_teamspace_filter.query)
            .filter(workspace__slug=slug)
            .filter(receiver_id=user_id)
            .filter(entity_name__in=["issue", "epic"])
            .distinct()
        )

        q_filters = Q()

        # Apply snoozed filter
        now = timezone.now()
        snoozed = False if snoozed is None else snoozed
        if snoozed:
            q_filters &= Q(snoozed_till__isnull=False)
        else:
            q_filters &= Q(snoozed_till__lt=now) | Q(snoozed_till__isnull=True)

        # Apply archived filter
        archived = False if archived is None else archived
        if archived:
            q_filters &= Q(archived_at__isnull=False)
        else:
            q_filters &= Q(archived_at__isnull=True)

        # Apply read filter
        if read is not None:
            if read == "true":
                q_filters &= Q(read_at__isnull=False)
            elif read == "false":
                q_filters &= Q(read_at__isnull=True)

        # Apply mentioned filter
        if mentioned is not None:
            if mentioned:
                q_filters &= Q(sender__icontains="mentioned")
            else:
                q_filters &= ~Q(sender__icontains="mentioned")

        type_q_filters = Q()
        if type is not None and type != "all":
            filter_type = type.split(",")

            # Subscribed issues subquery
            if "subscribed" in filter_type:
                subscribed_subquery = (
                    IssueSubscriber.objects.filter(
                        workspace__slug=slug, subscriber_id=user_id, issue_id=OuterRef("entity_identifier")
                    )
                    .annotate(
                        created=Exists(
                            Issue.objects.filter(created_by=user, pk=OuterRef("issue_id")).filter(
                                Q(type__isnull=True) | Q(type__is_epic=False)
                            )
                        )
                    )
                    .annotate(
                        assigned=Exists(IssueAssignee.objects.filter(issue_id=OuterRef("issue_id"), assignee=user))
                    )
                    .filter(created=False, assigned=False)
                )

                type_q_filters |= Q(entity_identifier__in=subscribed_subquery.values("issue_id"))

            # Assigned issues subquery
            if "assigned" in filter_type:
                assigned_subquery = IssueAssignee.objects.filter(
                    workspace__slug=slug, assignee_id=user_id, issue_id=OuterRef("entity_identifier")
                )

                type_q_filters |= Q(entity_identifier__in=assigned_subquery.values("issue_id"))

            # Created issues subquery
            if "created" in filter_type:
                has_permission = await sync_to_async(
                    WorkspaceMember.objects.filter(
                        workspace__slug=slug,
                        member=user,
                        role__lt=15,
                        is_active=True,
                    ).exists
                )()
                if has_permission:
                    notification_queryset = notification_queryset.none()
                else:
                    created_subquery = Issue.objects.filter(
                        workspace__slug=slug, created_by=user, pk=OuterRef("entity_identifier")
                    ).filter(Q(type__isnull=True) | Q(type__is_epic=False))

                    type_q_filters |= Q(entity_identifier__in=created_subquery.values("pk"))

        q = q_filters & type_q_filters
        notification_queryset = notification_queryset.filter(q)

        intake_issue_subquery = IntakeIssue.objects.filter(
            issue_id=OuterRef("entity_identifier"),
            issue__workspace__slug=slug,
            status__in=[0, 2, -2],
        ).values("id")[:1]

        epic_issue_subquery = Issue.objects.filter(
            pk=OuterRef("entity_identifier"),
            workspace__slug=slug,
            type__isnull=False,
            type__is_epic=True,
        ).values("pk")[:1]

        notification_queryset = notification_queryset.annotate(
            is_intake_issue=Exists(intake_issue_subquery),
            is_epic_issue=Exists(epic_issue_subquery),
            intake_id=Subquery(
                IntakeIssue.objects.filter(
                    issue_id=OuterRef("entity_identifier"),
                    issue__workspace__slug=slug,
                    status__in=[0, 2, -2],
                ).values("id")[:1]
            ),
        )

        notification_count_queryset = copy.deepcopy(notification_queryset)
        notification_queryset = (
            notification_queryset.select_related("workspace", "project", "triggered_by", "receiver")
            .prefetch_related(
                "project__project_projectmember",
                "project__project_projectmember__member",
            )
            .order_by("snoozed_till", "-created_at")
        )

        return await query_paginate_async(
            base_queryset=notification_count_queryset,
            query_set=notification_queryset,
            cursor=cursor,
        )
