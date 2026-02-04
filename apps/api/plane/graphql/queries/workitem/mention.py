# Third-party imports
import strawberry

# Strawberry imports
from strawberry.permission import PermissionExtension
from strawberry.types import Info

# Module imports
from plane.graphql.helpers import get_work_item_mention_async
from plane.graphql.permissions.workspace import WorkspaceBasePermission
from plane.graphql.types.workitem import WorkItemMentionType


@strawberry.type
class WorkspaceWorkItemMentionQuery:
    @strawberry.field(extensions=[PermissionExtension(permissions=[WorkspaceBasePermission()])])
    async def workspace_work_item_mention(self, info: Info, slug: str, workitem: str) -> WorkItemMentionType:
        user = info.context.user
        user_id = str(user.id)

        work_item = await get_work_item_mention_async(
            user_id=user_id,
            workspace_slug=slug,
            work_item_id=workitem,
        )

        if not work_item:
            return None

        return WorkItemMentionType(
            id=work_item.id,
            name=work_item.name,
            sequence_id=work_item.sequence_id,
            project_id=work_item.project_id,
            type_id=work_item.type_id if work_item.type else None,
            project_identifier=work_item.project.identifier,
            state_group=work_item.state.group if work_item.state else None,
            state_name=work_item.state.name if work_item.state else None,
        )
