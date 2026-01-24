# Python imports
from typing import List, Dict, Any
from uuid import UUID
import json

# Module imports
from plane.ee.models import Initiative
from plane.db.models import (
    UserNotificationPreference,
    WorkspaceMember,
)
from plane.utils.notifications.base import (
    SubscriberData,
    BaseNotificationHandler,
    ActivityData,
)


class InitiativeNotificationHandler(BaseNotificationHandler):
    """
    Notification handler for Initiatives.
    Handles all initiative-related notifications including mentions, assignments, and property changes.
    """

    # Entity configuration
    ENTITY_NAME = "initiative"
    ENTITY_MODEL = Initiative
    SUBSCRIBER_MODEL = None  # Initiatives don't have a subscriber model yet
    MENTION_MODEL = None  # Initiatives don't have mention tracking
    ACTIVITY_MODEL = None  # Will be set if needed

    # Activity types that should not trigger notifications
    EXCLUDED_ACTIVITY_TYPES = [
        "initiative_reaction.activity.created",
        "initiative_reaction.activity.deleted",
        "comment_reaction.activity.created",
        "comment_reaction.activity.deleted",
    ]

    # Cleaning methods
    @classmethod
    def normalize_activity_data(cls, activity_dict: Dict) -> Dict:
        """
        Normalize initiative-specific activity keys to generic keys.
        """
        normalized = activity_dict.copy()
        # Add any initiative-specific normalization here if needed
        return normalized

    # ==================== Entity Loading ====================

    def load_entity(self):
        """Load the initiative"""
        self.entity = Initiative.objects.filter(pk=self.context.entity_id).first()

    def get_entity_display_name(self) -> str:
        """Get display name for the initiative"""
        return self.entity.name if self.entity else ""

    def get_entity_data(self) -> Dict[str, Any]:
        """Get initiative data for notification payload"""
        if not self.entity:
            return {}

        return {
            "id": str(self.context.entity_id),
            "name": str(self.entity.name),
            "logo_props": self.entity.logo_props,
        }

    def get_entity_type(self) -> str:
        """Return 'initiative'"""
        return "initiative"

    # ==================== Member & Subscriber Management ====================

    def load_project(self):
        """Override: Initiatives are not project-scoped"""
        self.project = None

    def get_active_members(self) -> List[UUID]:
        """Get list of active workspace members"""
        if not self.context.workspace_id:
            return []

        return list(
            WorkspaceMember.objects.filter(
                workspace_id=self.context.workspace_id, is_active=True, member__is_bot=False
            ).values_list("member_id", flat=True)
        )

    def get_subscribers(self, exclude_users: List[str]) -> SubscriberData:
        """Get initiative lead as subscriber"""
        subscribers = []

        # Get the initiative lead
        if self.entity and self.entity.lead_id and self.entity.lead_id != UUID(self.context.actor_id):
            subscribers.append(self.entity.lead_id)

        return SubscriberData(
            subscribers=subscribers,
        )

    def create_subscribers(self, mentions: List[str]) -> List:
        """
        Initiatives don't auto-subscribe users on mention.
        Returns empty list.
        """
        return []

    # ==================== Mention Processing ====================

    def process_entity_mentions(self) -> Dict[str, Dict[str, Any]]:
        """
        Process mentions for initiative-specific fields (description and comments).
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
            current_mentions = self.extract_mentions(requested_data.get("description_html", ""))

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
        Initiatives don't persist mention records.
        No-op implementation.
        """
        pass

    # ==================== Email Preferences ====================

    def should_send_email(self, preference: UserNotificationPreference, activity: ActivityData) -> bool:
        """
        Determine if email should be sent based on user preferences and activity type.
        """
        # Comments
        if activity.field == "comment":
            return preference.comment

        # All other property changes
        elif preference.property_change:
            return True

        return False
