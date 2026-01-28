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
};

interface ITotalWorklogResponse {
  total_worklog: number;
}

export const IssueTotalWorklog = (props: TIssueTotalWorklog) => {
  const { workspaceSlug, projectId, issueId } = props;
  const { t } = useTranslation();
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
    // Definimos una función interna para el inicio
    const initiateFetch = async () => {
      await fetchTotal();
    };

    // Usamos void para ejecutarla
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
    <div className="flex min-h-8 gap-2">
      <div className="flex w-2/5 flex-shrink-0 gap-1 pt-2 text-sm text-custom-text-300">
        <Icon name="project.clock" className="h-4 w-4 flex-shrink-0" />
        <span>{t("tracked_time") || "Total worklog"}</span>
      </div>

      <div className="h-full min-h-8 w-3/5 flex-grow pt-2 text-sm font-medium text-custom-text-100">
        {hours}h {minutes}m
      </div>
    </div>
  );
};
