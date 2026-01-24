from plane.ee.views.base import BaseAPIView
from plane.ee.permissions.page import ProjectPagePermission, TeamspacePagePermission, WorkspacePagePermission
from plane.db.models import PageLog, Issue, ProjectPage, Page
from plane.ee.models import TeamspacePage
from rest_framework.response import Response
from rest_framework import status


class PageEmbedEndpoint(BaseAPIView):
    def get_permissions(self):
        """
        Dynamically return permission classes based on whether project_id or team_space_id is provided.
        """
        if self.request.query_params.get("project_id") is not None:
            # Add project_id to kwargs so ProjectPagePermission can access it
            self.kwargs["project_id"] = self.request.query_params.get("project_id")
            return [ProjectPagePermission()]
        elif self.request.query_params.get("team_space_id") is not None:
            # Add team_space_id to kwargs so TeamspacePagePermission can access it
            self.kwargs["team_space_id"] = self.request.query_params.get("team_space_id")
            return [TeamspacePagePermission()]
        return [WorkspacePagePermission()]

    def get(self, request, slug, page_id, **_kwargs):
        embed_type = request.query_params.get("embed_type", "issue")

        # check if page_id is a project_id or team_space_id
        if request.query_params.get("project_id") is not None:
            project_id = request.query_params.get("project_id")
            if not ProjectPage.objects.filter(page_id=page_id, workspace__slug=slug, project_id=project_id).exists():
                return Response(
                    {"error": "Project page not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        elif request.query_params.get("teamspace_id") is not None:
            teamspace_id = request.query_params.get("teamspace_id")
            if not TeamspacePage.objects.filter(
                page_id=page_id, workspace__slug=slug, team_space_id=teamspace_id
            ).exists():
                return Response(
                    {"error": "Teamspace page not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            if not Page.objects.filter(id=page_id, workspace__slug=slug, is_global=True).exists():
                return Response(
                    {"error": "Page not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Validate embed_type against PageLog TYPE_CHOICES
        valid_embed_types = ["issue", "page"]
        if embed_type not in valid_embed_types:
            return Response(
                {"error": "Invalid embed type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Handle different embed types
        if embed_type == "issue":
            page_logs = (
                PageLog.objects.filter(page_id=page_id, workspace__slug=slug)
                .filter(entity_name="issue")
                .values_list("entity_identifier", flat=True)
            )
            issues = (
                Issue.issue_objects.filter(id__in=list(page_logs), workspace__slug=slug)
                .select_related("state")
                .values(
                    "name",
                    "id",
                    "sequence_id",
                    "project__identifier",
                    "project_id",
                    "priority",
                    "state__group",
                    "state__name",
                    "state__color",
                    "type_id",
                )
            )
            return Response(issues, status=status.HTTP_200_OK)

        else:
            return Response(
                {"error": f"Embed type '{embed_type}' is not yet implemented"},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )


class PageMentionEndpoint(BaseAPIView):
    def get_permissions(self):
        """
        Dynamically return permission classes based on whether project_id or team_space_id is provided.
        """
        if self.request.query_params.get("project_id") is not None:
            # Add project_id to kwargs so ProjectPagePermission can access it
            self.kwargs["project_id"] = self.request.query_params.get("project_id")
            return [ProjectPagePermission()]
        elif self.request.query_params.get("team_space_id") is not None:
            # Add team_space_id to kwargs so TeamspacePagePermission can access it
            self.kwargs["team_space_id"] = self.request.query_params.get("team_space_id")
            return [TeamspacePagePermission()]
        return [WorkspacePagePermission()]

    def get(self, request, slug, page_id, **_kwargs):
        mention_type = request.query_params.get("mention_type", "issue_mention")

        # check if page_id is a project_id or team_space_id
        if request.query_params.get("project_id") is not None:
            project_id = request.query_params.get("project_id")
            if not ProjectPage.objects.filter(page_id=page_id, workspace__slug=slug, project_id=project_id).exists():
                return Response(
                    {"error": "Project page not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        elif request.query_params.get("teamspace_id") is not None:
            teamspace_id = request.query_params.get("teamspace_id")
            if not TeamspacePage.objects.filter(
                page_id=page_id, workspace__slug=slug, team_space_id=teamspace_id
            ).exists():
                return Response(
                    {"error": "Teamspace page not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            if not Page.objects.filter(id=page_id, workspace__slug=slug, is_global=True).exists():
                return Response(
                    {"error": "Page not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Validate mention_type
        valid_mention_types = ["issue_mention", "user_mention"]
        if mention_type not in valid_mention_types:
            return Response(
                {"error": "Invalid mention type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Handle different mention types
        if mention_type == "issue_mention":
            page_logs = (
                PageLog.objects.filter(page_id=page_id, workspace__slug=slug)
                .filter(entity_name="issue_mention")
                .values_list("entity_identifier", flat=True)
            )
            issues = (
                Issue.issue_objects.filter(id__in=list(page_logs), workspace__slug=slug)
                .select_related("state")
                .values(
                    "id",
                    "name",
                    "sequence_id",
                    "project__identifier",
                    "project_id",
                    "state__group",
                    "state__name",
                    "state__color",
                    "type_id",
                )
            )
            return Response(issues, status=status.HTTP_200_OK)

        else:
            return Response(
                {"error": f"Mention type '{mention_type}' is not yet implemented"},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )
