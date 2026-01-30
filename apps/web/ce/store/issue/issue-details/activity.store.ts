import { orderBy, set, uniq } from "lodash-es";
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
}

export interface TIssueWorklog {
  id: string;
  created_at: string;
  duration: number;
  description: string;
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
  ): Promise<TIssueActivity[]> {
    try {
      this.loader = loaderType;

      let props = {};
      const currentActivityIds = this.getActivitiesByIssueId(issueId);
      if (currentActivityIds && currentActivityIds.length > 0) {
        const currentActivity = this.getActivityById(currentActivityIds[currentActivityIds.length - 1]);
        if (currentActivity) props = { created_at__gt: currentActivity.created_at };
      }

      // 1. Forzamos el tipado de la respuesta de la API
      const [activities, worklogs] = (await Promise.all([
        this.issueActivityService.getIssueActivities(workspaceSlug, projectId, issueId, props),
        this.issueActivityService.getIssueWorklogs(workspaceSlug, projectId, issueId),
      ])) as [TIssueActivity[], TIssueWorklog[]];

      const activityIds = activities.map((a) => a.id);
      const worklogIds = worklogs.map((w) => w.id);

      runInAction(() => {
        // 2. Reemplazamos lodash/update y concat por lógica nativa de TS
        // Esto evita que la variable se vuelva 'any'
        const existingIds = this.activities[issueId] || [];
        this.activities[issueId] = uniq([...existingIds, ...activityIds]);

        // 3. Usamos asignación directa en lugar de lodash/set
        activities.forEach((activity) => {
          this.activityMap[activity.id] = activity;
        });

        this.worklogs[issueId] = worklogIds;
        worklogs.forEach((w) => {
          this.worklogMap[w.id] = w;
        });

        this.loader = undefined;
      });

      // 4. Retornamos la variable original que TS ya sabe que es TIssueActivity[]
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
      return worklogs;
    } catch (error) {
      console.error("Error al cargar worklogs en el store", error);
      return undefined;
    }
  }
}
