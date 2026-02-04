# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.db.models import Page
from plane.ee.models import PageUser
from plane.ee.views.base import BaseViewSet
from plane.app.serializers import PageUserSerializer
from plane.ee.permissions import ProjectPagePermission
from plane.ee.bgtasks.export_page_task import page_export_task


class ProjectPageExportViewSet(BaseViewSet):
    serializer_class = PageUserSerializer
    model = PageUser
    permission_classes = [ProjectPagePermission]

    def create(self, request, slug, project_id, page_id):
        page = Page.objects.get(pk=page_id, workspace__slug=slug)
        if not page:
            return Response(
                {"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # run a celery task to export the page and all the sub pages
        page_export_task.delay(
            email=request.user.email,
            slug=slug,
            page_id=page_id,
            project_id=project_id,
            type="PROJECT",
            user_id=request.user.id,
        )

        return Response(
            {
                "message": f"Once the export is ready it will be emailed to you at {str(request.user.email)}"
            },
            status=status.HTTP_200_OK,
        )
