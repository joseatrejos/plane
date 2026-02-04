# Third party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from plane.ee.views.base import BaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.db.models import ExporterHistory, IssueView
from plane.bgtasks.export_task import issue_export_task
from plane.payment.flags.flag import FeatureFlag
from plane.payment.flags.flag_decorator import check_feature_flag


class ProjectViewExportEndpoint(BaseAPIView):

    """
    Export view from a project view endpoint.
    with filters and rich filters
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER,])
    @check_feature_flag(FeatureFlag.ADVANCED_EXPORTS)
    def post(self, request, slug, project_id, view_id):

        # Get the provider
        provider = request.data.get("provider", False)

        if provider not in ["csv", "xlsx", "json"]:
            return Response(
                {"error": f"Provider '{provider}' not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the view
        view = IssueView.objects.get(pk=view_id)

        # Get the filters
        filters = view.filters
        rich_filters = view.rich_filters

        # Create the exporter
        exporter = ExporterHistory.objects.create(
            workspace_id=view.workspace_id,
            project=[project_id],
            initiated_by=request.user,
            provider=provider,
            type="view_exports",
            filters=filters,
            rich_filters=rich_filters,
        )

        # Trigger the export task for view issues
        issue_export_task.delay(
            provider=exporter.provider,
            workspace_id=view.workspace_id,
            project_ids=[project_id],
            token_id=exporter.token,
            multiple=False,
            slug=slug,
            export_type="issue",
        )

        # Return the response
        return Response(
            {"message": "Once the export is ready you will be able to download it"},
            status=status.HTTP_200_OK,
        )


class WorkspaceViewExportEndpoint(BaseAPIView):

    """
    Export view from a workspace view endpoint.
    with filters and rich filters
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER,], level="WORKSPACE")
    def post(self, request, slug, view_id):

        # Get the provider
        provider = request.data.get("provider", False)

        if provider not in ["csv", "xlsx", "json"]:
            return Response(
                {"error": f"Provider '{provider}' not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the view
        view = IssueView.objects.get(pk=view_id)

        # Get the filters
        filters = view.filters
        rich_filters = view.rich_filters

        # Create the exporter
        exporter = ExporterHistory.objects.create(
            workspace_id=view.workspace_id,
            initiated_by=request.user,
            provider=provider,
            type="view_exports",
            filters=filters,
            rich_filters=rich_filters,
        )

        # Trigger the export task for view issues
        issue_export_task.delay(
            provider=exporter.provider,
            workspace_id=view.workspace_id,
            project_ids=[],
            token_id=exporter.token,
            multiple=False,
            slug=slug,
            export_type="issue",
        )

        # Return the response
        return Response(
            {"message": "Once the export is ready you will be able to download it"},
            status=status.HTTP_200_OK,
        )