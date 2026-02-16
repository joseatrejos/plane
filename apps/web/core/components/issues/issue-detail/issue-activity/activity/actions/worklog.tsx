import type { KeyboardEvent, ReactNode } from "react";
import { useState } from "react";
import { observer } from "mobx-react";
import { Network } from "lucide-react";
import axios, { AxiosError } from "axios";
import { Tooltip } from "@plane/propel/tooltip";
import { Avatar } from "@plane/ui";
import { useTranslation } from "@/hooks/use-translation";
import { API_BASE_URL } from "@plane/constants";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { renderFormattedTime, renderFormattedDate, calculateTimeAgo, getFileURL } from "@plane/utils";
import { usePlatformOS } from "@/hooks/use-platform-os";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useMember } from "@/hooks/store/use-member";
import { useLabel } from "@/hooks/store/use-label";
import { WorklogQuickActions } from "./helpers/worklog";
import { LabelActivityChip } from "./label-activity-chip";
import type { TIssueWorklog } from "@/plane-web/store/issue/issue-details/activity.store";
import { Icon } from "@plane/propel/icons";
import { WorklogForm } from "@/plane-web/components/issues/worklog/activity/worklog-form";

// Define proper types for the worklog data
interface ActorDetail {
  id?: string;
  first_name?: string;
  is_bot?: boolean;
  display_name?: string;
  avatar_url?: string;
}

interface Worklog {
  id: string;
  actor?: string;
  created_by?: string;
  logged_by?: string;
  actor_detail?: ActorDetail;
  created_at: string;
  duration: number;
  description?: string;
  label?: string | null;
  label_name?: string | null;
  label_color?: string | null;
}

type TWorklogBlockComponent = {
  icon?: ReactNode;
  worklog: Worklog;
  ends: "top" | "bottom" | undefined;
  inlineText?: ReactNode;
  descriptionBlock?: ReactNode;
  quickActions?: ReactNode;
  actorName?: string;
};

export function WorklogBlockComponent(props: TWorklogBlockComponent) {
  const { icon, worklog, ends, inlineText, descriptionBlock, quickActions, actorName } = props;
  const { isMobile } = usePlatformOS();
  const displayName = actorName ?? worklog.actor_detail?.display_name ?? "User";

  if (!worklog) return null;

  return (
    <div className={`group relative flex gap-3 ${ends === "top" ? `pb-2` : ends === "bottom" ? `pt-2` : `py-2`}`}>
      <div className="absolute left-[13px] top-0 bottom-0 w-0.5 bg-custom-background-80" aria-hidden />
      {/* CAMBIA ESTA PARTE - Elimina el bg-custom-background-80 y otros estilos cuando hay un ícono personalizado */}
      <div className="flex-shrink-0 w-7 h-7 flex justify-center items-center z-[4]">
        {icon ? (
          icon
        ) : (
          <div className="w-7 h-7 rounded-full overflow-hidden flex justify-center items-center bg-custom-background-80 text-custom-text-200">
            <Network className="w-3.5 h-3.5" />
          </div>
        )}
      </div>

      {descriptionBlock ? (
        <div className="flex flex-col gap-3 flex-grow">
          <div className="flex w-full gap-2">
            <div className="flex-1 flex flex-wrap items-center gap-1 text-caption-sm-regular text-custom-text-300">
              <span className="font-medium text-custom-text-100">{displayName}</span>
              <span>
                {inlineText}{" "}
                <Tooltip
                  isMobile={isMobile}
                  tooltipContent={`${renderFormattedDate(worklog.created_at)}, ${renderFormattedTime(worklog.created_at)}`}
                >
                  <span className="whitespace-nowrap text-custom-text-350">{calculateTimeAgo(worklog.created_at)}</span>
                </Tooltip>
              </span>
            </div>
            {quickActions && <div className="flex-shrink-0">{quickActions}</div>}
          </div>
          <div className="mb-2 text-body-sm-regular bg-layer-2 border border-subtle shadow-raised-100 rounded-lg p-3">
            {descriptionBlock}
          </div>
        </div>
      ) : (
        <div className="w-full flex items-start justify-between gap-2">
          <div className="flex-1 text-caption-sm-regular text-custom-text-300">
            <span className="font-medium text-custom-text-100">{displayName}</span>
            <span> {inlineText} </span>
            <span>
              <Tooltip
                isMobile={isMobile}
                tooltipContent={`${renderFormattedDate(worklog.created_at)}, ${renderFormattedTime(worklog.created_at)}`}
              >
                <span className="whitespace-nowrap text-custom-text-350">{calculateTimeAgo(worklog.created_at)}</span>
              </Tooltip>
            </span>
          </div>

          {quickActions && <div className="flex-shrink-0">{quickActions}</div>}
        </div>
      )}
    </div>
  );
}

interface IssueActivityWorklogProps {
  activityComment: Worklog;
  ends: "top" | "bottom" | undefined;
  workspaceSlug: string;
  projectId: string;
  issueId: string;
}

export const IssueActivityWorklog = observer(function IssueActivityWorklog(props: IssueActivityWorklogProps) {
  const { activityComment, ends } = props;
  // store hooks
  const {
    activity: { addWorklog, removeWorklog },
    issue: { getIssueById },
  } = useIssueDetail();
  const { getUserDetails } = useMember();
  const { getLabelById } = useLabel();
  const { t } = useTranslation() as { t: (key: string) => string };
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editHours, setEditHours] = useState("");
  const [editMinutes, setEditMinutes] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editLabelId, setEditLabelId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const issue = getIssueById(props.issueId);
  const labelOptions =
    issue?.label_ids
      ?.map((id) => getLabelById(id))
      .filter((label): label is { id: string; name: string; color?: string } => Boolean(label))
      .map((label) => ({ id: label.id, name: label.name, color: label.color })) ?? [];
  const shouldShowLabelSelect = labelOptions.length > 0;

  if (!activityComment) return null;

  const worklogUserId = activityComment.logged_by ?? activityComment.created_by ?? activityComment.actor;
  const userDetails = getUserDetails(worklogUserId);
  const displayName = activityComment.actor_detail?.is_bot
    ? activityComment.actor_detail?.first_name + ` ${t("bot")}`
    : (userDetails?.display_name ?? activityComment.actor_detail?.display_name);
  const avatarUrl = userDetails?.avatar_url ?? activityComment.actor_detail?.avatar_url;

  const hours = Math.floor(activityComment.duration / 60);
  const minutes = activityComment.duration % 60;
  const activeLabelDetails = activityComment.label ? getLabelById(activityComment.label) : null;
  const labelDetails =
    activeLabelDetails ??
    (activityComment.label_name
      ? {
          name: activityComment.label_name,
          color: activityComment.label_color ?? undefined,
        }
      : null);

  const openEditPopover = () => {
    const initialHours = Math.floor(activityComment.duration / 60);
    const initialMinutes = activityComment.duration % 60;
    setEditHours(initialHours ? String(initialHours) : "");
    setEditMinutes(initialMinutes ? String(initialMinutes) : "");
    setEditDescription(activityComment.description ?? "");
    setEditLabelId(activityComment.label ?? null);
    setIsEditOpen(true);
  };

  const handleUpdate = async (close?: () => void) => {
    if (!activityComment.id) return;
    const h = Number(editHours) || 0;
    const m = Number(editMinutes) || 0;
    const duration = Math.max(0, Math.floor(h * 60 + m));

    if (!duration) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("common.error.label"),
        message: t("worklog.validation.add_duration") || "Please add a duration",
      });
      return;
    }

    if (shouldShowLabelSelect && !editLabelId) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("common.error.label"),
        message: t("worklog.validation.select_label") || "Please select a label",
      });
      return;
    }

    setIsSaving(true);
    const url = `${API_BASE_URL}/api/workspaces/${props.workspaceSlug}/projects/${props.projectId}/issues/${props.issueId}/worklogs/${activityComment.id}/`;

    try {
      const payload: { duration: number; description: string; label?: string | null } = {
        duration,
        description: editDescription,
      };
      if (shouldShowLabelSelect) payload.label = editLabelId;

      const response = await axios.patch<TIssueWorklog>(url, payload, { withCredentials: true });
      addWorklog(props.issueId, response.data);
      window.dispatchEvent(new CustomEvent("worklog_updated"));
      close?.();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("success"),
        message: t("worklog.success.updated") || "Worklog updated",
      });
    } catch (err) {
      const error = err as AxiosError<{ detail?: string }>;
      const message = error.response?.data?.detail || error.message || "Failed to update worklog";
      setToast({ type: TOAST_TYPE.ERROR, title: t("common.error.label"), message });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    const url = `${API_BASE_URL}/api/workspaces/${props.workspaceSlug}/projects/${props.projectId}/issues/${props.issueId}/worklogs/${activityComment.id}/`;
    try {
      await axios.delete(url, { withCredentials: true });
      removeWorklog(props.issueId, activityComment.id);
      window.dispatchEvent(new CustomEvent("worklog_updated"));
      setIsEditOpen(false);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("success"),
        message: t("worklog.success.deleted") || "Worklog deleted",
      });
    } catch (err) {
      const error = err as AxiosError<{ detail?: string }>;
      const message = error.response?.data?.detail || error.message || "Failed to delete worklog";
      setToast({ type: TOAST_TYPE.ERROR, title: t("common.error.label"), message });
    }
  };

  const timeLoggedText = (
    <>
      logged{" "}
      <span className="font-medium text-custom-text-100">
        {hours}h {minutes}m
      </span>{" "}
      of work
      {labelDetails ? (
        <>
          {" "}
          <LabelActivityChip name={labelDetails.name} color={labelDetails.color} />
        </>
      ) : null}
    </>
  );

  const handleEditKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleUpdate(() => setIsEditOpen(false));
    }
  };

  const editPopover = isEditOpen && (
    <div className="absolute right-0 top-full z-20 mt-2">
      <WorklogForm
        hours={editHours}
        minutes={editMinutes}
        description={editDescription}
        labelId={editLabelId}
        labelOptions={labelOptions}
        onLabelChange={setEditLabelId}
        showLabelSelect={shouldShowLabelSelect}
        onHoursChange={setEditHours}
        onMinutesChange={setEditMinutes}
        onDescriptionChange={setEditDescription}
        onSave={() => void handleUpdate(() => setIsEditOpen(false))}
        onCancel={() => setIsEditOpen(false)}
        isSaving={isSaving}
        saveButtonText={t("update") || "Update"}
        onKeyDown={handleEditKeyDown}
      />
    </div>
  );

  const quickActions = (
    <div className="relative">
      <WorklogQuickActions onEdit={openEditPopover} onDelete={() => void handleDelete()} />
      {editPopover}
    </div>
  );

  // Si hay descripcion, mostrar como comentario con bloque de texto
  if (activityComment.description) {
    return (
      <>
        <WorklogBlockComponent
          worklog={activityComment}
          icon={
            <div className="relative w-7 h-7">
              <Avatar
                name={displayName ?? "User"}
                src={getFileURL(avatarUrl ?? "")}
                size="base"
                showTooltip={false}
                className="flex-shrink-0 border border-custom-border-200"
              />
              <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-custom-background-100 rounded-full border border-custom-border-200 flex items-center justify-center">
                <Icon name="project.clock" className="h-2.5 w-2.5 text-custom-text-300" />
              </div>
            </div>
          }
          ends={ends}
          inlineText={timeLoggedText}
          actorName={displayName ?? "User"}
          descriptionBlock={
            <div className="text-base bg-custom-background-100 border-custom-border-200 p-3">
              {activityComment.description}
            </div>
          }
          quickActions={quickActions}
        />
      </>
    );
  }

  return (
    <>
      <WorklogBlockComponent
        worklog={activityComment}
        icon={
          <div className="relative w-7 h-7">
            <Avatar
              name={displayName ?? "User"}
              src={getFileURL(avatarUrl ?? "")}
              size="base"
              showTooltip={false}
              className="flex-shrink-0 border border-custom-border-200"
            />
            <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-custom-background-100 rounded-full border border-custom-border-200 flex items-center justify-center">
              <Icon name="project.clock" className="h-2.5 w-2.5 text-custom-text-300" />
            </div>
          </div>
        }
        ends={ends}
        inlineText={timeLoggedText}
        actorName={displayName ?? "User"}
        quickActions={quickActions}
      />
    </>
  );
});
