from django.urls import path

from plane.ee.views.app import (
    MilestoneViewSet,
    MilestoneWorkItemsEndpoint,
    MilestoneWorkItemsSearchEndpoint,
    WorkItemMilestoneEndpoint,
)

urlpatterns = [
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/milestones/",
        MilestoneViewSet.as_view({"get": "list", "post": "create"}),
        name="project-milestones",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/milestones/<uuid:milestone_id>/work-items/",
        MilestoneWorkItemsEndpoint.as_view(),
        name="project-milestone-work-items",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/milestones/work-items/search/",
        MilestoneWorkItemsSearchEndpoint.as_view(),
        name="project-milestone-work-items-search",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/work-items/<uuid:work_item_id>/milestone/",
        WorkItemMilestoneEndpoint.as_view(),
        name="project-milestone-update-work-item-milestone",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/milestones/<uuid:pk>/",
        MilestoneViewSet.as_view(
            {
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="project-milestone",
    ),
]
