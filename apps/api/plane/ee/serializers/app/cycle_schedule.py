from plane.ee.models import CycleSettings
from plane.ee.serializers import BaseSerializer
from django.utils import timezone
from rest_framework import serializers


class AutomatedCycleSerializer(BaseSerializer):

    class Meta:
        model = CycleSettings
        fields = "__all__"
        read_only_fields = [
            "workspace",
            "project",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        # start date cannot be in the past
        if (
            data.get("start_date", None) is not None
            and data.get("start_date", None).date() < timezone.now().date()
        ):
            raise serializers.ValidationError("Start date cannot be in the past")

        # cycle duration will be in multiple of 7 days
        if (
            data.get("cycle_duration", None) is not None
            and data.get("cycle_duration", None) % 7 != 0
        ):
            raise serializers.ValidationError(
                "Cycle duration must be in multiple of 7 days"
            )

        # the number of cycles to be scheduled in the future cannot be greater than 3
        if (
            data.get("number_of_cycles", None) is not None
            and data.get("number_of_cycles", None) > 3
        ):
            raise serializers.ValidationError(
                "Number of cycles to be scheduled in the future cannot be greater than 3"
            )

        return data
