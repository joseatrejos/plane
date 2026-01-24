# Django imports
from django.urls import path

# Module imports
from plane.ee.views import (
    IntakePublishedIssueEndpoint,
    IntakeMetaPublishedIssueEndpoint,
    IntakeFormSettingsEndpoint,
    IntakeFormCreateWorkItemEndpoint,
)

urlpatterns = [
    path(
        "anchor/<str:anchor>/intake/meta/",
        IntakeMetaPublishedIssueEndpoint.as_view(),
        name="intake-public-meta",
    ),
    path(
        "anchor/<str:anchor>/intake/",
        IntakePublishedIssueEndpoint.as_view(),
        name="intake-public",
    ),
    path(
        "anchor/<str:anchor>/intake/form/settings/",
        IntakeFormSettingsEndpoint.as_view(),
        name="intake-public-form-settings",
    ),
    path(
        "anchor/<str:anchor>/intake/form/",
        IntakeFormCreateWorkItemEndpoint.as_view(),
        name="intake-public-form-create",
    ),
]
