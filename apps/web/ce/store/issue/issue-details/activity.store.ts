import { concat, orderBy, set, uniq, update } from "lodash-es";
import { action, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
// plane package imports
import type { E_SORT_ORDER } from "@plane/constants";
import { EActivityFilterType } from "@plane/constants";
import type {
  TIssueActivityComment,
  TIssueActivity,
  TIssueActivityMap,
  TIssueActivityIdMap,
  TIssueServiceType,
} from "@plane/types";
import { EIssueServiceType } from "@plane/types";
// plane web constants
// services
import { IssueActivityService } from "@/services/issue";
// store
import type { CoreRootStore } from "@/store/root.store";

export type TActivityLoader = "fetch" | "mutate" | undefined;

export interface IIssueActivityStoreActions {
  // actions
  fetchActivities: (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    loaderType?: TActivityLoader
  ) => Promise<TIssueActivity[]>;
  fetchWorklogs: (workspaceSlug: string, projectId: string, issueId: string) => Promise<TIssueWorklog[] | undefined>;
  addWorklog: (issueId: string, worklog: TIssueWorklog) => void;
  removeWorklog: (issueId: string, worklogId: string) => void;
}

export interface TIssueWorklog {
  id: string;
  created_at: string;
  duration: number;
  description: string;
  created_by?: string;
  logged_by?: string;
  label?: string | null;
}

export interface IIssueActivityStore extends IIssueActivityStoreActions {
  // observables
  loader: TActivityLoader;
  activities: TIssueActivityIdMap;
  activityMap: TIssueActivityMap;
  worklogs: TIssueActivityIdMap;
  worklogMap: Record<string, TIssueWorklog>;
  // helper methods
  getActivitiesByIssueId: (issueId: string) => string[] | undefined;
  getActivityById: (activityId: string) => TIssueActivity | undefined;
  getWorklogById: (worklogId: string) => TIssueWorklog | undefined;
  getActivityAndCommentsByIssueId: (issueId: string, sortOrder: E_SORT_ORDER) => TIssueActivityComment[] | undefined;
}

export class IssueActivityStore implements IIssueActivityStore {
  // observables
  loader: TActivityLoader = "fetch";
  activities: TIssueActivityIdMap = {};
  activityMap: TIssueActivityMap = {};

  worklogs: TIssueActivityIdMap = {};
  worklogMap: Record<string, TIssueWorklog> = {};
  // services
  serviceType;
  issueActivityService;

  constructor(
    protected store: CoreRootStore,
    serviceType: TIssueServiceType = EIssueServiceType.ISSUES
  ) {
    makeObservable(this, {
      // observables
      loader: observable.ref,
      activities: observable,
      activityMap: observable,
      worklogs: observable,
      worklogMap: observable,
      // actions
      fetchActivities: action,
      addWorklog: action,
      removeWorklog: action,
    });
    this.serviceType = serviceType;
    // services
    this.issueActivityService = new IssueActivityService(this.serviceType);
  }

  // helper methods
  getActivitiesByIssueId = (issueId: string) => {
    if (!issueId) return undefined;
    return this.activities[issueId] ?? undefined;
  };

  getActivityById = (activityId: string) => {
    if (!activityId) return undefined;
    return this.activityMap[activityId] ?? undefined;
  };

  getWorklogById = (worklogId: string) => {
    if (!worklogId) return undefined;
    return this.worklogMap[worklogId] ?? undefined;
  };

  addWorklog = (issueId: string, worklog: TIssueWorklog) => {
    if (!issueId || !worklog?.id) return;
    const currentIds = this.worklogs[issueId] ?? [];
    set(this.worklogs, issueId, uniq(concat(currentIds, [worklog.id])));
    set(this.worklogMap, worklog.id, worklog);
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("worklog_updated"));
    }
  };

  removeWorklog = (issueId: string, worklogId: string) => {
    if (!issueId || !worklogId) return;
    const currentIds = this.worklogs[issueId] ?? [];
    set(
      this.worklogs,
      issueId,
      currentIds.filter((id) => id !== worklogId)
    );
    if (this.worklogMap[worklogId]) delete this.worklogMap[worklogId];
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("worklog_updated"));
    }
  };

  protected buildActivityAndCommentItems(issueId: string): TIssueActivityComment[] | undefined {
    if (!issueId) return undefined;

    const activityComments: TIssueActivityComment[] = [];

    const currentStore =
      this.serviceType === EIssueServiceType.EPICS ? this.store.issue.epicDetail : this.store.issue.issueDetail;

    const activities = this.getActivitiesByIssueId(issueId);
    const comments = currentStore.comment.getCommentsByIssueId(issueId);

    const worklogIds = this.worklogs[issueId] || [];

    if (!activities || !comments) return undefined;

    activities.forEach((activityId) => {
      const activity = this.getActivityById(activityId);
      if (!activity) return;
      const type =
        activity.field === "state"
          ? EActivityFilterType.STATE
          : activity.field === "assignees"
            ? EActivityFilterType.ASSIGNEE
            : activity.field === null
              ? EActivityFilterType.DEFAULT
              : EActivityFilterType.ACTIVITY;
      activityComments.push({
        id: activity.id,
        activity_type: type,
        created_at: activity.created_at,
      });
    });

    comments.forEach((commentId) => {
      const comment = currentStore.comment.getCommentById(commentId);
      if (!comment) return;
      activityComments.push({
        id: comment.id,
        activity_type: EActivityFilterType.COMMENT,
        created_at: comment.created_at,
      });
    });

    worklogIds.forEach((worklogId) => {
      const worklog = this.worklogMap[worklogId];
      if (!worklog) return;
      activityComments.push({
        id: worklog.id,
        activity_type: EActivityFilterType.WORKLOG, // Este es el tipo que activamos en el filtro
        created_at: worklog.created_at,
        duration: worklog.duration, // Pasamos la duración
        description: worklog.description, // Pasamos la descripción
        created_by: worklog.created_by,
        logged_by: worklog.logged_by,
        label: worklog.label ?? null,
      });
    });

    return activityComments;
  }

  protected sortActivityComments(items: TIssueActivityComment[], sortOrder: E_SORT_ORDER): TIssueActivityComment[] {
    return orderBy(items, (e) => new Date(e.created_at || 0), sortOrder);
  }

  getActivityAndCommentsByIssueId = computedFn((issueId: string, sortOrder: E_SORT_ORDER) => {
    const baseItems = this.buildActivityAndCommentItems(issueId);
    if (!baseItems) return undefined;
    return this.sortActivityComments(baseItems, sortOrder);
  });

  // actions
  public async fetchActivities(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    loaderType: TActivityLoader = "fetch"
  ) {
    try {
      this.loader = loaderType;

      let props = {};
      const currentActivityIds = this.getActivitiesByIssueId(issueId);
      if (currentActivityIds && currentActivityIds.length > 0) {
        const currentActivity = this.getActivityById(currentActivityIds[currentActivityIds.length - 1]);
        if (currentActivity) props = { created_at__gt: currentActivity.created_at };
      }

      const activities = (await this.issueActivityService.getIssueActivities(
        workspaceSlug,
        projectId,
        issueId,
        props
      ));
      const worklogs = (await this.issueActivityService.getIssueWorklogs(
        workspaceSlug,
        projectId,
        issueId
      )) as TIssueWorklog[];

      const activityIds = activities.map((activity) => activity.id);
      const worklogIds = worklogs.map((w) => w.id);

      runInAction(() => {
        update(this.activities, issueId, (currentActivityIds) => {
          if (!currentActivityIds) return activityIds;
          // eslint-disable-next-line @typescript-eslint/no-unsafe-return
          return uniq(concat(currentActivityIds, activityIds));
        });
        activities.forEach((activity) => {
          set(this.activityMap, activity.id, activity);
        });

        set(this.worklogs, issueId, worklogIds);
        worklogs.forEach((w) => {
          set(this.worklogMap, w.id, w);
        });

        this.loader = undefined;
      });
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("worklog_updated"));
      }

      return activities;
    } catch (error) {
      this.loader = undefined;
      throw error;
    }
  }

  public async fetchWorklogs(
    workspaceSlug: string,
    projectId: string,
    issueId: string
  ): Promise<TIssueWorklog[] | undefined> {
    try {
      const worklogs = (await this.issueActivityService.getIssueWorklogs(
        workspaceSlug,
        projectId,
        issueId
      )) as TIssueWorklog[];

      runInAction(() => {
        const ids = worklogs.map((w) => w.id);
        set(this.worklogs, issueId, ids);
        worklogs.forEach((w) => {
          set(this.worklogMap, w.id, w);
        });
      });
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("worklog_updated"));
      }
      return worklogs;
    } catch (error) {
      console.error("Error al cargar worklogs en el store", error);
      return undefined;
    }
  }
}
