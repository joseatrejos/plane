import type { ReactNode } from "react";
import { useState } from "react";
import { observer } from "mobx-react";
import { Network } from "lucide-react";
import axios, { AxiosError } from "axios";
import { Tooltip } from "@plane/propel/tooltip";
import { Avatar, EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
import { useTranslation } from "@plane/i18n";
import { API_BASE_URL } from "@plane/constants";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { renderFormattedTime, renderFormattedDate, calculateTimeAgo, getFileURL } from "@plane/utils";
import { usePlatformOS } from "@/hooks/use-platform-os";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useMember } from "@/hooks/store/use-member";
import { WorklogQuickActions } from "./helpers/worklog";
import type { TIssueWorklog } from "@/plane-web/store/issue/issue-details/activity.store";

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
      <div className="flex-shrink-0 ring-6 w-7 h-7 rounded-full overflow-hidden flex justify-center items-center z-[4] bg-custom-background-80 text-custom-text-200">
        {icon ? icon : <Network className="w-3.5 h-3.5" />}
      </div>

      {descriptionBlock ? (
        <div className="flex flex-col gap-3 flex-grow">
          <div className="flex w-full gap-2">
            <div className="flex-1 flex flex-wrap items-center gap-1">
              <span className="text-xs font-medium">{displayName}</span>
              <div className="text-xs text-custom-text-300">
                {inlineText}{" "}
                <Tooltip
                  isMobile={isMobile}
                  tooltipContent={`${renderFormattedDate(worklog.created_at)}, ${renderFormattedTime(worklog.created_at)}`}
                >
                  <span className="whitespace-nowrap text-custom-text-350">{calculateTimeAgo(worklog.created_at)}</span>
                </Tooltip>
              </div>
            </div>
            {quickActions && <div className="flex-shrink-0">{quickActions}</div>}
          </div>
          <div className="mb-2">{descriptionBlock}</div>
        </div>
      ) : (
        <div className="w-full flex items-start justify-between gap-2">
          <div className="flex-1 text-custom-text-200 text-xs">
            <span className="text-custom-text-100 font-medium">{displayName}</span>
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
  } = useIssueDetail();
  const { getUserDetails } = useMember();
  const { t } = useTranslation();
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editHours, setEditHours] = useState("");
  const [editMinutes, setEditMinutes] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  if (!activityComment) return null;


  const worklogUserId = activityComment.logged_by ?? activityComment.created_by ?? activityComment.actor;
  const userDetails = getUserDetails(worklogUserId);
  const displayName = activityComment.actor_detail?.is_bot
    ? activityComment.actor_detail?.first_name + ` ${t("bot")}`
    : (userDetails?.display_name ?? activityComment.actor_detail?.display_name);
  const avatarUrl = userDetails?.avatar_url ?? activityComment.actor_detail?.avatar_url;

  const hours = Math.floor(activityComment.duration / 60);
  const minutes = activityComment.duration % 60;

  const openEditModal = () => {
    const initialHours = Math.floor(activityComment.duration / 60);
    const initialMinutes = activityComment.duration % 60;
    setEditHours(initialHours ? String(initialHours) : "");
    setEditMinutes(initialMinutes ? String(initialMinutes) : "");
    setEditDescription(activityComment.description ?? "");
    setIsEditOpen(true);
  };

  const handleUpdate = async () => {
    if (!activityComment.id) return;
    const h = Number(editHours) || 0;
    const m = Number(editMinutes) || 0;
    const duration = Math.max(0, Math.floor(h * 60 + m));

    if (!duration) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("common.error.label"),
        message: t("please_add_duration") || "Please add a duration",
      });
      return;
    }

    setIsSaving(true);
    const url = `${API_BASE_URL}/api/workspaces/${props.workspaceSlug}/projects/${props.projectId}/issues/${props.issueId}/worklogs/${activityComment.id}/`;

    try {
      const response = await axios.patch<TIssueWorklog>(
        url,
        { duration, description: editDescription },
        { withCredentials: true }
      );
      addWorklog(props.issueId, response.data);
      window.dispatchEvent(new CustomEvent("worklog_updated"));
      setIsEditOpen(false);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("success"),
        message: t("worklog_success_saved") || "Worklog updated",
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
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("success"),
        message: t("worklog_success_deleted") || "Worklog deleted",
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
    </>
  );

  // Si hay descripción, mostrar como comentario con bloque de texto
  if (activityComment.description) {
    return (
      <>
        <WorklogBlockComponent
          worklog={activityComment}
          icon={
            <Avatar
              name={displayName ?? "User"}
              src={getFileURL(avatarUrl ?? "")}
              size="base"
              showTooltip={false}
              className="flex-shrink-0"
            />
          }
          ends={ends}
          inlineText={timeLoggedText}
          actorName={displayName ?? "User"}
          descriptionBlock={
            <div className="text-base bg-custom-background-100 rounded border border-custom-border-200 p-3">
              {activityComment.description}
            </div>
          }
          quickActions={<WorklogQuickActions onEdit={openEditModal} onDelete={() => void handleDelete()} />}
        />
        <ModalCore
          isOpen={isEditOpen}
          handleClose={() => setIsEditOpen(false)}
          position={EModalPosition.CENTER}
          width={EModalWidth.SM}
          className="rounded-lg max-w-[20rem]"
        >
          <div className="p-4 bg-custom-background-100 border border-custom-border-200 rounded-md shadow-lg space-y-4">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-2 py-1 bg-custom-background-80 rounded-full border border-custom-border-200">
                <span className="text-[11px] font-medium text-custom-text-200">
                  {editHours || 0}h {editMinutes || 0}m
                </span>
              </div>
            </div>

            <div className="flex gap-2">
              <input
                type="number"
                placeholder="Hours"
                value={editHours}
                onChange={(e) => setEditHours(e.target.value)}
                className="w-full bg-custom-background-90 border border-custom-border-200 rounded px-2 py-1 text-sm outline-none focus:border-custom-primary-100 text-custom-text-100"
              />
              <input
                type="number"
                placeholder="Minutes"
                value={editMinutes}
                onChange={(e) => setEditMinutes(e.target.value)}
                className="w-full bg-custom-background-90 border border-custom-border-200 rounded px-2 py-1 text-sm outline-none focus:border-custom-primary-100 text-custom-text-100"
              />
            </div>

            <textarea
              placeholder="Description..."
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              className="w-full bg-custom-background-90 border border-custom-border-200 rounded p-2 text-sm min-h-[80px] outline-none focus:border-custom-primary-100 text-custom-text-100 resize-none"
            />

            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="px-3 py-1 text-sm text-custom-text-200 hover:bg-custom-background-80 rounded transition-colors"
                onClick={() => setIsEditOpen(false)}
                disabled={isSaving}
              >
                {t("cancel") || "Cancel"}
              </button>
              <button
                type="button"
                className="px-4 py-1 text-sm bg-custom-primary-100 text-white rounded hover:bg-custom-primary-200 transition-colors font-medium"
                onClick={() => void handleUpdate()}
                disabled={isSaving}
              >
                {isSaving ? t("save") || "Updating..." : t("update") || "Update"}
              </button>
            </div>
          </div>
        </ModalCore>
      </>
    );
  }

  return (
    <>
      <WorklogBlockComponent
        worklog={activityComment}
        icon={
          <Avatar
            name={displayName ?? "User"}
            src={getFileURL(avatarUrl ?? "")}
            size="base"
            showTooltip={false}
            className="flex-shrink-0"
          />
        }
        ends={ends}
        inlineText={timeLoggedText}
        actorName={displayName ?? "User"}
        quickActions={<WorklogQuickActions onEdit={openEditModal} onDelete={() => void handleDelete()} />}
      />
      <ModalCore
        isOpen={isEditOpen}
        handleClose={() => setIsEditOpen(false)}
        position={EModalPosition.CENTER}
        width={EModalWidth.SM}
        className="rounded-lg max-w-[20rem]"
      >
        <div className="p-4 bg-custom-background-100 border border-custom-border-200 rounded-md shadow-lg space-y-4">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-custom-background-80 rounded-full border border-custom-border-200">
              <span className="text-[11px] font-medium text-custom-text-200">
                {editHours || 0}h {editMinutes || 0}m
              </span>
            </div>
          </div>

          <div className="flex gap-2">
            <input
              type="number"
              placeholder="Hours"
              value={editHours}
              onChange={(e) => setEditHours(e.target.value)}
              className="w-full bg-custom-background-90 border border-custom-border-200 rounded px-2 py-1 text-sm outline-none focus:border-custom-primary-100 text-custom-text-100"
            />
            <input
              type="number"
              placeholder="Minutes"
              value={editMinutes}
              onChange={(e) => setEditMinutes(e.target.value)}
              className="w-full bg-custom-background-90 border border-custom-border-200 rounded px-2 py-1 text-sm outline-none focus:border-custom-primary-100 text-custom-text-100"
            />
          </div>

          <textarea
            placeholder="Description..."
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
            className="w-full bg-custom-background-90 border border-custom-border-200 rounded p-2 text-sm min-h-[80px] outline-none focus:border-custom-primary-100 text-custom-text-100 resize-none"
          />

          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="px-3 py-1 text-sm text-custom-text-200 hover:bg-custom-background-80 rounded transition-colors"
              onClick={() => setIsEditOpen(false)}
              disabled={isSaving}
            >
              {t("cancel") || "Cancel"}
            </button>
            <button
              type="button"
              className="px-4 py-1 text-sm bg-custom-primary-100 text-white rounded hover:bg-custom-primary-200 transition-colors font-medium"
              onClick={() => void handleUpdate()}
              disabled={isSaving}
            >
              {isSaving ? t("save") || "Updating..." : t("update") || "Update"}
            </button>
          </div>
        </div>
      </ModalCore>
    </>
  );
});
