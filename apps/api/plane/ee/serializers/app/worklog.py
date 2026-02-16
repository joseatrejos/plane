# Module imports
from rest_framework import serializers
from plane.app.serializers.base import BaseSerializer
from plane.ee.models import IssueWorkLog
from plane.db.models import IssueLabel, Label
from plane.ee.serializers import IssueLiteSerializer


class IssueWorkLogSerializer(BaseSerializer):
    issue_detail = IssueLiteSerializer(read_only=True, source="issue")
    label_name = serializers.SerializerMethodField()
    label_color = serializers.SerializerMethodField()

    class Meta:
        model = IssueWorkLog
        fields = [
            "id",
            "created_at",
            "updated_at",
            "description",
            "duration",
            "label",
            "label_name",
            "label_color",
            "created_by",
            "updated_by",
            "project_id",
            "workspace_id",
            "logged_by",
            "issue_detail",
        ]
        read_only_fields = ["logged_by", "issue", "workspace", "project"]

    def get_label_name(self, obj):
        if not obj.label_id:
            return None
        return Label.all_objects.filter(id=obj.label_id).values_list("name", flat=True).first()

    def get_label_color(self, obj):
        if not obj.label_id:
            return None
        label_data = Label.all_objects.filter(id=obj.label_id).values("color", "deleted_at").first()
        if not label_data:
            return None
        if label_data.get("deleted_at") is not None:
            return None
        return label_data.get("color")

    def validate(self, data):
        issue_id = getattr(self.instance, "issue_id", None) or self.context.get("issue_id")
        if not issue_id:
            return data

        issue_label_qs = IssueLabel.objects.filter(issue_id=issue_id)
        has_labels = issue_label_qs.exists()

        if self.instance is None and has_labels and data.get("label") is None:
            raise serializers.ValidationError("Label is required for worklog when issue has labels")

        if "label" in data:
            label_value = data.get("label")
            if has_labels and label_value is None:
                raise serializers.ValidationError("Label is required for worklog when issue has labels")
            if label_value is not None:
                label_id = getattr(label_value, "id", label_value)
                if not issue_label_qs.filter(label_id=label_id).exists():
                    raise serializers.ValidationError("Label is not associated with this issue")

        return data


class ProjectWorklogSummarySerializer(serializers.Serializer):
    """Serializer for project worklog summary with aggregated duration per issue"""

    issue_id = serializers.UUIDField(help_text="ID of the work item")
    duration = serializers.IntegerField(
        help_text="Total duration logged for this work item in seconds"
    )
