# Module imports
from plane.ee.views.base import BaseAPIView
from plane.payment.flags.flag_decorator import check_feature_flag
from plane.app.permissions import allow_permission, ROLE
from plane.payment.flags.flag import FeatureFlag
from plane.db.models import Workspace
from plane.ee.models import InitiativeLabel
from plane.ee.serializers import InitiativeLabelSerializer


# Third party imports
from rest_framework import status
from rest_framework.response import Response


class InitiativeLabelsEndpoint(BaseAPIView):
    @check_feature_flag(FeatureFlag.INITIATIVES)
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=self.kwargs.get("slug"))

        initiative_labels = InitiativeLabel.objects.filter(workspace_id=workspace.id)

        serializer = InitiativeLabelSerializer(initiative_labels, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @check_feature_flag(FeatureFlag.INITIATIVES)
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=self.kwargs.get("slug"))

        serializer = InitiativeLabelSerializer(data=request.data, context={"workspace_id": workspace.id})

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @check_feature_flag(FeatureFlag.INITIATIVES)
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def patch(self, request, slug, initiative_label_id):
        workspace = Workspace.objects.get(slug=self.kwargs.get("slug"))

        initiative_label = InitiativeLabel.objects.get(id=initiative_label_id, workspace__slug=slug)

        serializer = InitiativeLabelSerializer(
            initiative_label,
            data=request.data,
            partial=True,
            context={"workspace_id": workspace.id},
        )

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @check_feature_flag(FeatureFlag.INITIATIVES)
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def delete(self, request, slug, initiative_label_id):
        initiative_label = InitiativeLabel.objects.get(id=initiative_label_id, workspace__slug=slug)

        initiative_label.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
