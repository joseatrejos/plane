# Third party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from plane.ee.views.base import BaseAPIView
from plane.app.permissions import ROLE, allow_permission
from plane.db.models import ExporterHistory, Workspace
from plane.bgtasks.export_task import issue_export_task
from plane.payment.flags.flag import FeatureFlag
from plane.payment.flags.flag_decorator import check_feature_flag


class ProjectIntakeExportEndpoint(BaseAPIView):

    """
    Export intake from a project intake endpoint.
    with filters and rich filters
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER,])
    @check_feature_flag(FeatureFlag.ADVANCED_EXPORTS)
    def post(self, request, slug, project_id):
        # Get the provider
        provider = request.data.get("provider", False)

        # Get the rich filters
        rich_filters = request.data.get("rich_filters", None)

        if provider not in ["csv", "xlsx", "json"]:
            return Response(
                {"error": f"Provider '{provider}' not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Pass the intake_status filter to the exporter
        filters = {
            "is_intake_workitem": "true",
        }

        # Get the workspace
        workspace = Workspace.objects.get(slug=slug)

        # Create the exporter
        exporter = ExporterHistory.objects.create(
            workspace=workspace,
            project=[project_id],
            initiated_by=request.user,
            provider=provider,
            type="intake_exports",
            filters=filters,
            rich_filters=rich_filters,
        )

        # Trigger the export task for project intake
        issue_export_task.delay(
            provider=exporter.provider,
            workspace_id=workspace.id,
            project_ids=[project_id],
            token_id=exporter.token,
            multiple=False,
            slug=slug,
            export_type="intake",
        )

        # Return the response
        return Response(
            {"message": "Once the export is ready you will be able to download it"},
            status=status.HTTP_200_OK,
        )
