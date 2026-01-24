# Django imports
from django.urls import path

# Module imports
from plane.ee.views import IssueWorklogAPIEndpoint, ProjectWorklogAPIEndpoint


old_url_patterns = [
    # Deprecated url path
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/worklogs/",
        IssueWorklogAPIEndpoint.as_view(http_method_names=["post", "get"]),
        name="worklogs",
    ),
    # Deprecated url path
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issues/<uuid:issue_id>/worklogs/<uuid:pk>/",
        IssueWorklogAPIEndpoint.as_view(http_method_names=["patch", "delete"]),
        name="worklogs",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/total-worklogs/",
        ProjectWorklogAPIEndpoint.as_view(http_method_names=["get"]),
        name="project-worklogs",
    ),
]

new_url_patterns = [
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/work-items/<uuid:issue_id>/worklogs/",
        IssueWorklogAPIEndpoint.as_view(http_method_names=["post", "get"]),
        name="work-item-worklogs",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/work-items/<uuid:issue_id>/worklogs/<uuid:pk>/",
        IssueWorklogAPIEndpoint.as_view(http_method_names=["patch", "delete"]),
        name="work-item-worklog-detail",
    ),
]

urlpatterns = old_url_patterns + new_url_patterns
