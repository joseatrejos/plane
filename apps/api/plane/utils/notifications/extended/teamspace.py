# Python imports
from typing import List, Dict, Any, Optional
from uuid import UUID
import json

# Django imports
from django.db.models import Subquery

# Module imports
from plane.ee.models import Teamspace, TeamspaceMember
from plane.db.models import (
    UserNotificationPreference,
    WorkspaceMember,
)
from plane.utils.notifications.base import (
    SubscriberData,
    BaseNotificationHandler,
    ActivityData,
)


class TeamspaceNotificationHandler(BaseNotificationHandler):
    """
    Notification handler for Teamspaces.
    Handles all teamspace-related notifications including mentions, member changes, and property changes.
    """

    # Entity configuration
    ENTITY_NAME = "teamspace"
    ENTITY_MODEL = Teamspace
    SUBSCRIBER_MODEL = TeamspaceMember
    MENTION_MODEL = None  # Teamspaces don't have mention tracking
    ACTIVITY_MODEL = None  # Will be set if needed

    # Activity types that should not trigger notifications
    EXCLUDED_ACTIVITY_TYPES = [
        "comment_reaction.activity.created",
        "comment_reaction.activity.deleted",
    ]

    # Cleaning methods
    @classmethod
    def normalize_activity_data(cls, activity_dict: Dict) -> Dict:
        """
        Normalize teamspace-specific activity keys to generic keys.
        """
        normalized = activity_dict.copy()
        # Add any teamspace-specific normalization here if needed
        return normalized

    # ==================== Entity Loading ====================

    def load_entity(self):
        """Load the teamspace"""
        self.entity = Teamspace.objects.filter(pk=self.context.entity_id).first()

    def get_entity_display_name(self) -> str:
        """Get display name for the teamspace"""
        return self.entity.name if self.entity else ""

    def get_entity_data(self) -> Dict[str, Any]:
        """Get teamspace data for notification payload"""
        if not self.entity:
            return {}

        return {
            "id": str(self.context.entity_id),
            "name": str(self.entity.name),
            "logo_props": self.entity.logo_props,
        }

    def get_entity_type(self) -> str:
        """Return 'teamspace'"""
        return "teamspace"

    # ==================== Member & Subscriber Management ====================

    def load_project(self):
        """Override: Teamspaces are not project-scoped"""
        self.project = None

    def get_active_members(self) -> List[UUID]:
        """Get list of active workspace members"""
        if not self.context.workspace_id:
            return []

        return list(
            WorkspaceMember.objects.filter(
                workspace_id=self.context.workspace_id, is_active=True,
                member__is_bot=False
            ).values_list("member_id", flat=True)
        )

    def get_subscribers(self, exclude_users: List[str]) -> SubscriberData:
        """Get teamspace members and lead"""
        # Get teamspace members
        subscribers = list(
            TeamspaceMember.objects.filter(
                team_space_id=self.context.entity_id,
                member__in=Subquery(
                    WorkspaceMember.objects.filter(
                        workspace_id=self.context.workspace_id, is_active=True
                    ).values("member_id")
                ),
            )
            .exclude(member_id__in=exclude_users)
            .values_list("member", flat=True)
        )

        # Remove duplicates and convert to UUIDs
        subscribers = list(set(subscribers))

        # Remove actor from the list
        subscribers = [
            subscriber
            for subscriber in subscribers
            if subscriber != UUID(self.context.actor_id)
        ]

        return SubscriberData(
            subscribers=subscribers,
        )

    def create_subscribers(self, mentions: List[str]) -> List:
        """
        Teamspaces don't auto-subscribe users on mention.
        Returns empty list.
        """
        return []

    # ==================== Mention Processing ====================

    def process_entity_mentions(self) -> Dict[str, Dict[str, Any]]:
        """
        Process mentions for teamspace-specific fields (description and comments).
        """
        results = {}

        # 1. Process description mentions (JSON format)
        if self.context.current_instance and self.context.requested_data:
            current_instance = json.loads(self.context.current_instance)
            requested_data = json.loads(self.context.requested_data)

            description_mentions = self.process_mentions(
                old_value=current_instance.get("description_html"),
                new_value=requested_data.get("description_html"),
                filter_to_active=True,
            )

            # Get all current mentions
            current_mentions = self.extract_mentions(
                requested_data.get("description_html", "")
            )

            if description_mentions.new_mentions or current_mentions:
                results["description"] = {
                    "new_mentions": description_mentions.new_mentions,
                    "removed_mentions": description_mentions.removed_mentions,
                    "all_mentions": current_mentions,
                    "notification_type": "description",
                }

        # 2. Process comment mentions
        comment_mentions_new = []
        comment_mentions_all = []

        for activity in self.context.activities:
            # Check if this activity is for a comment
            if activity.field == "comment" and activity.verb in ["created", "updated"]:
                mention_data = self.process_mentions(
                    old_value=activity.old_value,
                    new_value=activity.new_value,
                    filter_to_active=True,
                )

                comment_mentions_new.extend(mention_data.new_mentions)

                if activity.new_value:
                    all_mentions = self.extract_mentions(activity.new_value)
                    comment_mentions_all.extend(all_mentions)

        if comment_mentions_new or comment_mentions_all:
            results["comment"] = {
                "new_mentions": comment_mentions_new,
                "all_mentions": comment_mentions_all,
                "notification_type": "comment",
            }

        return results

    def update_all_mentions(self, mention_results: Dict[str, Dict[str, Any]]):
        """
        Teamspaces don't persist mention records.
        No-op implementation.
        """
        pass

    # ==================== Email Preferences ====================

    def should_send_email(
        self, preference: UserNotificationPreference, activity: ActivityData
    ) -> bool:
        """
        Determine if email should be sent based on user preferences and activity type.
        """
        # Comments
        if activity.field == "comment":
            return preference.comment

        # Pages
        elif activity.field == "page":
            return True

        # All other property changes
        elif preference.property_change:
            return True

        return False

    # ==================== Notification Data Building ====================

    def build_notification_data(self, activity: ActivityData) -> Dict[str, Any]:
        """Build notification data for teamspace"""
        return {
            self.ENTITY_NAME: self.get_entity_data(),
            f"{self.ENTITY_NAME}_activity": {
                "id": str(activity.id),
                "verb": str(activity.verb),
                "field": str(activity.field),
                "actor": str(activity.actor_id),
                "new_value": str(activity.new_value),
                "old_value": str(activity.old_value),
                "old_identifier": (
                    str(activity.old_identifier) if activity.old_identifier else None
                ),
                "new_identifier": (
                    str(activity.new_identifier) if activity.new_identifier else None
                ),
            },
        }

    def build_email_data(
        self, activity: ActivityData, field_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build email data with additional workspace info"""
        data = super().build_email_data(activity, field_override)

        # Add email-specific fields for teamspaces
        if "teamspace" in data and self.workspace:
            data["teamspace"]["workspace_slug"] = str(self.workspace.slug)

        return data