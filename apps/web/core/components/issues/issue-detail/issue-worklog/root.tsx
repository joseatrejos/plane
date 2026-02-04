import { useEffect, useState, useCallback } from "react";
import axios from "axios";
// plane imports
import { API_BASE_URL } from "@plane/constants";
import { Icon } from "@plane/propel/icons";
import { useTranslation } from "@plane/i18n";

export type TIssueTotalWorklog = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  labelClassName?: string;
  gapClassName?: string;
};
interface ITotalWorklogResponse {
  total_worklog: number;
}

export const IssueTotalWorklog = (props: TIssueTotalWorklog) => {
  // Set defaults that match your "Sidebar" (w-1/4)
  const { workspaceSlug, projectId, issueId, labelClassName = "w-1/4", gapClassName = "gap-3" } = props;

  const { t } = useTranslation() as { t: (key: string) => string };
  const [totalMinutes, setTotalMinutes] = useState<number | null>(null);

  const fetchTotal = useCallback(async () => {
    try {
      const response = await axios.get<ITotalWorklogResponse>(
        `${API_BASE_URL}/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/total-worklogs/`,
        { withCredentials: true }
      );
      setTotalMinutes(response.data.total_worklog ?? 0);
    } catch (e) {
      console.error("Error fetching total worklog", e);
    }
  }, [workspaceSlug, projectId, issueId]);

  useEffect(() => {
    const initiateFetch = async () => {
      await fetchTotal();
    };
    void initiateFetch();

    const handleUpdate = () => {
      void fetchTotal();
    };

    window.addEventListener("worklog_updated", handleUpdate);
    return () => {
      window.removeEventListener("worklog_updated", handleUpdate);
    };
  }, [fetchTotal]);

  if (totalMinutes === null) return null;

  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  return (
    <div className={`flex w-full items-center ${gapClassName} min-h-8`}>
      <div
        className={`flex shrink-0 items-center gap-1.5 w-30 text-body-xs-regular text-tertiary h-7.5 ${labelClassName}`}
      >
        <Icon name="project.clock" className="size-4 shrink-0" />
        <span>{t("worklog.tracked_time") || "Total worklog"}</span>
      </div>

      <div className="flex flex-grow flex-col gap-3 truncate">
        <div className="px-2 text-sm text-placeholder">
          {hours}h {minutes}m
        </div>
      </div>
    </div>
  );
};
