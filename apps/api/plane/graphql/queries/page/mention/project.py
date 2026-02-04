# Python imports
from typing import List, Optional

# Third-party imports
import strawberry

# Strawberry imports
from strawberry.permission import PermissionExtension
from strawberry.types import Info

# Module imports
from plane.graphql.helpers.page import get_page_mention_async, get_page_mentions_async
from plane.graphql.permissions.project import ProjectBasePermission
from plane.graphql.types.page import PageMentionEntityNameEnum, PageMentionType


@strawberry.type
class ProjectPageMentionQuery:
    @strawberry.field(extensions=[PermissionExtension(permissions=[ProjectBasePermission()])])
    async def project_page_mentions(
        self,
        info: Info,
        slug: str,
        project: str,
        page: str,
        entity_name: Optional[List[PageMentionEntityNameEnum]] = None,
    ) -> List[PageMentionType]:
        user = info.context.user
        user_id = str(user.id)

        page_mentions = await get_page_mentions_async(
            user_id=user_id,
            workspace_slug=slug,
            project_id=project,
            page_id=page,
            entity_name=entity_name,
        )

        return page_mentions

    @strawberry.field(extensions=[PermissionExtension(permissions=[ProjectBasePermission()])])
    async def project_page_mention(
        self, info: Info, slug: str, project: str, page: str, mention: str
    ) -> PageMentionType:
        user = info.context.user
        user_id = str(user.id)

        page_mention = await get_page_mention_async(
            user_id=user_id,
            workspace_slug=slug,
            project_id=project,
            page_id=page,
            mention_id=mention,
        )

        return page_mention
