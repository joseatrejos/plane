import { API_BASE_URL } from "@plane/constants";
import type { TIssueActivity, TIssueServiceType, TIssueWorklog } from "@plane/types";
import { EIssueServiceType } from "@plane/types";
import { APIService } from "@/services/api.service";
// types
// helper

// Define a proper error type for API errors
interface APIError {
  response?: {
    data?: unknown;
  };
}

export class IssueActivityService extends APIService {
  private serviceType: TIssueServiceType;

  constructor(serviceType: TIssueServiceType = EIssueServiceType.ISSUES) {
    super(API_BASE_URL);
    this.serviceType = serviceType;
  }

  async getIssueActivities(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    params:
      | {
          created_at__gt: string;
        }
      | object = {}
  ): Promise<TIssueActivity[]> {
    // 1. Pasamos el genérico <TIssueActivity[]> al método get
    return this.get<TIssueActivity[]>(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/${this.serviceType}/${issueId}/history/`,
      {
        params: {
          activity_type: `${this.serviceType === EIssueServiceType.EPICS ? "epic-property" : "issue-property"}`,
          ...params,
        },
      }
    )
      .then((response) => {
        // 2. Al usar el genérico arriba, response ya es TIssueActivity[]
        // Retornamos un array vacío si la respuesta es nula para evitar 'any'
        return response || [];
      })
      .catch((error: APIError) => {
        throw error?.response?.data;
      });
  }

  async getIssueWorklogs(workspaceSlug: string, projectId: string, issueId: string): Promise<TIssueWorklog[]> {
    return this.get<TIssueWorklog[]>(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/worklogs/`
    )
      .then((response) => {
        return response || [];
      })
      .catch((error: APIError) => {
        throw error?.response?.data;
      });
  }
}
