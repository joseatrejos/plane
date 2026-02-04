from .asset import urlpatterns as asset_patterns
from .epic import urlpatterns as epic_patterns
from .job import urlpatterns as job_patterns
from .page import urlpatterns as page_patterns
from .worklog import urlpatterns as worklog_patterns
from .workspace import urlpatterns as workspace_patterns
from .work_item_property import urlpatterns as work_item_property_patterns

urlpatterns = [
    *asset_patterns,
    *epic_patterns,
    *job_patterns,
    *page_patterns,
    *worklog_patterns,
    *workspace_patterns,
    *work_item_property_patterns,
]
