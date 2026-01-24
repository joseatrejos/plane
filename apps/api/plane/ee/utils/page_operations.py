"""
Utility functions for page operations across different page types
(workspace, project, teamspace pages).

These functions handle both single page operations and bulk operations
for transferring pages and sub-pages with a unified, optimized approach.

Usage Examples:

    # Single page operations (e.g., in move.py)
    from plane.ee.utils.page_operations import (
        delete_teamspace_page,
        create_project_page,
        move_page_entities,
    )

    delete_teamspace_page([page_id], workspace_id)
    create_project_page([page_id], project_id, workspace_id, user_id)
    move_page_entities([page_id], "project", slug, user_id, project_id=project_id)

    # Bulk operations for sub-pages (e.g., in page_update.py background task)
    from plane.ee.utils.page_operations import (
        delete_teamspace_page,
        create_project_page,
        move_page_entities,
    )

    descendant_ids = ['page-id-1', 'page-id-2', 'page-id-3']
    delete_teamspace_page(descendant_ids, workspace_id)
    create_project_page(descendant_ids, project_id, workspace_id, user_id)
    move_page_entities(descendant_ids, "project", slug, user_id, project_id=project_id)
"""

from typing import List, Optional
from django.utils import timezone

from plane.db.models import (
    Page,
    ProjectPage,
    ProjectMember,
    FileAsset,
    UserFavorite,
    DeployBoard,
    UserRecentVisit,
)
from plane.ee.models import (
    TeamspacePage,
    WorkItemPage,
    PageUser,
    TeamspaceMember,
    PageComment,
    PageCommentReaction,
)


# ====================
# Page Operations
# ====================


def unlink_pages_from_teamspace(page_ids: List[str], workspace_id: str) -> None:
    """Unlink TeamspacePage associations for one or more pages."""
    TeamspacePage.objects.filter(page_id__in=page_ids, workspace_id=workspace_id).delete()


def link_pages_to_teamspace(
    page_ids: List[str], teamspace_id: str, workspace_id: str, user_id: str, batch_size: int = 10
) -> None:
    """Create TeamspacePage associations for one or more pages."""
    TeamspacePage.objects.bulk_create(
        [
            TeamspacePage(
                team_space_id=teamspace_id,
                page_id=page_id,
                workspace_id=workspace_id,
                created_by_id=user_id,
                updated_by_id=user_id,
            )
            for page_id in page_ids
        ],
        batch_size=batch_size,
        ignore_conflicts=True,
    )


def unlink_pages_from_project(page_ids: List[str], workspace_id: str) -> None:
    """unlink ProjectPage associations for one or more pages."""
    ProjectPage.objects.filter(page_id__in=page_ids, workspace_id=workspace_id).delete()


def link_pages_to_project(
    page_ids: List[str], project_id: str, workspace_id: str, user_id: str, batch_size: int = 10
) -> None:
    """Create ProjectPage associations for one or more pages."""
    ProjectPage.objects.bulk_create(
        [
            ProjectPage(
                project_id=project_id,
                page_id=page_id,
                workspace_id=workspace_id,
                created_by_id=user_id,
                updated_by_id=user_id,
            )
            for page_id in page_ids
        ],
        batch_size=batch_size,
        ignore_conflicts=True,
    )


def make_pages_workspace_level(page_ids: List[str], workspace_id: str, user_id: str) -> None:
    """make one or more pages workspace-level pages by setting is_global to True."""
    Page.objects.filter(id__in=page_ids, workspace_id=workspace_id).update(
        is_global=True,
        updated_by_id=user_id,
        updated_at=timezone.now(),
    )


def remove_pages_from_workspace_level(page_ids: List[str], workspace_id: str, user_id: str) -> None:
    """remove workspace-level status from one or more pages by setting is_global to False."""
    Page.objects.filter(id__in=page_ids, workspace_id=workspace_id).update(
        is_global=False,
        updated_by_id=user_id,
        updated_at=timezone.now(),
    )

# ====================
# Unified Entity Move Operations
# ====================


def move_page_entities(
    page_ids: List[str],
    move_type: str,
    slug: str,
    user_id: str,
    project_id: Optional[str] = None,
    teamspace_id: Optional[str] = None,
) -> None:
    """
    Unified function to move all page-related entities when pages are moved.
    Handles both single page and bulk operations efficiently.

    Args:
        page_ids: List of page IDs (can be a single ID in a list)
        move_type: Type of move - "project", "workspace", or "teamspace"
        slug: Workspace slug
        user_id: ID of the user performing the move
        project_id: ID of target project (required if move_type is "project")
        teamspace_id: ID of target teamspace (required if move_type is "teamspace")

    Raises:
        ValueError: If required parameters are missing for the move type
    """
    # Validate parameters based on move type
    if move_type == "project" and not project_id:
        raise ValueError("project_id is required when move_type is 'project'")
    if move_type == "teamspace" and not teamspace_id:
        raise ValueError("teamspace_id is required when move_type is 'teamspace'")

    # Determine target project_id (None for workspace/teamspace)
    target_project_id = project_id if move_type == "project" else None

    # Common update data
    update_data = {
        "project_id": target_project_id,
        "updated_by_id": user_id,
        "updated_at": timezone.now(),
    }

    # 1. Update WorkItemPage - delete old associations when moving from project
    if move_type in ["workspace", "teamspace"]:
        WorkItemPage.objects.filter(
            page_id__in=page_ids,
            workspace__slug=slug,
        ).delete()

    # 2. Update FileAsset
    FileAsset.objects.filter(page_id__in=page_ids, workspace__slug=slug).update(**update_data)

    # 3. Update DeployBoard
    DeployBoard.objects.filter(
        entity_identifier__in=page_ids,
        entity_name="page",
        workspace__slug=slug,
    ).update(**update_data)

    # 4. Handle PageUser - special logic for project/teamspace membership
    if move_type == "project":
        project_members = set(
            ProjectMember.objects.filter(
                project_id=project_id,
                is_active=True,
            ).values_list("member_id", flat=True)
        )

        # Remove users not in the project
        PageUser.objects.filter(page_id__in=page_ids, workspace__slug=slug).exclude(
            user_id__in=project_members
        ).delete()

    elif move_type == "teamspace":
        teamspace_members = set(
            TeamspaceMember.objects.filter(
                team_space_id=teamspace_id,
                workspace__slug=slug,
            ).values_list("member_id", flat=True)
        )

        # Remove users not in the teamspace
        PageUser.objects.filter(page_id__in=page_ids, workspace__slug=slug).exclude(
            user_id__in=teamspace_members
        ).delete()

    # Update remaining PageUser entries
    PageUser.objects.filter(page_id__in=page_ids, workspace__slug=slug).update(**update_data)

    # 5. Update PageComment
    PageComment.objects.filter(page_id__in=page_ids, workspace__slug=slug).update(**update_data)

    # 6. Update PageCommentReaction
    PageCommentReaction.objects.filter(comment__page_id__in=page_ids, workspace__slug=slug).update(**update_data)

    # 7. Update UserFavorite
    UserFavorite.objects.filter(
        entity_identifier__in=page_ids,
        entity_type="page",
        workspace__slug=slug,
    ).update(**update_data)

    # 8. Delete UserRecentVisit (always delete when moving)
    UserRecentVisit.objects.filter(
        entity_name="page",
        entity_identifier__in=page_ids,
        workspace__slug=slug,
    ).delete()



# ====================
# move entities to project, workspace, teamspace
# ====================


def move_entities_to_project(
    page_ids: List[str], slug: str, user_id: str, project_id: str
) -> None:
    """Move all entities for multiple pages to a project (bulk operation)."""
    move_page_entities(page_ids, "project", slug, user_id, project_id=project_id)


def move_entities_to_workspace(page_ids: List[str], slug: str, user_id: str) -> None:
    """Move all entities for multiple pages to workspace level (bulk operation)."""
    move_page_entities(page_ids, "workspace", slug, user_id)


def move_entities_to_teamspace(page_ids: List[str], slug: str, user_id: str, teamspace_id: str) -> None:
    """Move all entities for multiple pages to teamspace level (bulk operation)."""
    move_page_entities(page_ids, "teamspace", slug, user_id, teamspace_id=teamspace_id)
