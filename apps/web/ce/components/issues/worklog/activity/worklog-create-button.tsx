import { useState, KeyboardEvent } from "react";
import { Plus } from "lucide-react";
import axios, { AxiosError } from "axios";
// plane imports
import { Button } from "@plane/propel/button";
import { Popover } from "@plane/ui";
import { useTranslation } from "@/hooks/use-translation";
import { API_BASE_URL } from "@plane/constants";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useLabel } from "@/hooks/store/use-label";
import type { TIssueWorklog } from "@/plane-web/store/issue/issue-details/activity.store";
import { WorklogForm } from "./worklog-form";

type Props = {
  workspaceSlug?: string;
  projectId?: string;
  issueId?: string;
  disabled?: boolean;
  onCreated?: () => void;
};

export function IssueActivityWorklogCreateButton(props: Props) {
  const { disabled, workspaceSlug, projectId, issueId, onCreated } = props;
  const { t } = useTranslation() as { t: (key: string) => string };
  const {
    activity: { addWorklog },
    issue: { getIssueById },
  } = useIssueDetail();
  const { getLabelById } = useLabel();

  const [hours, setHours] = useState<string>("");
  const [minutes, setMinutes] = useState<string>("");
  const [description, setDescription] = useState("");
  const [labelId, setLabelId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const issue = issueId ? getIssueById(issueId) : undefined;
  const labelOptions =
    issue?.label_ids
      ?.map((id) => getLabelById(id))
      .filter((label): label is { id: string; name: string; color?: string } => Boolean(label))
      .map((label) => ({ id: label.id, name: label.name, color: label.color })) ?? [];
  const shouldShowLabelSelect = labelOptions.length > 0;

  const handleSave = async (closePopover?: () => void) => {
    const h = Number(hours) || 0;
    const m = Number(minutes) || 0;
    const duration = Math.max(0, Math.floor(h * 60 + m));

    if (!workspaceSlug || !projectId || !issueId) {
      setToast({ type: TOAST_TYPE.ERROR, title: t("common.error.label"), message: "Missing identifiers" });
      return;
    }

    if (duration <= 0) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("common.error.label"),
        message: t("worklog.validation.add_duration") || "Please add a duration",
      });
      return;
    }

    if (shouldShowLabelSelect && !labelId) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("common.error.label"),
        message: t("worklog.validation.select_label") || "Please select a label",
      });
      return;
    }

    setIsSaving(true);
    const url = `${API_BASE_URL}/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/worklogs/`;

    try {
      const payload = { duration, description, label: shouldShowLabelSelect ? labelId : null };
      const response = await axios.post<TIssueWorklog>(url, payload, { withCredentials: true });

      if (issueId) addWorklog(issueId, response.data);
      window.dispatchEvent(new CustomEvent("worklog_updated"));
      onCreated?.();

      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("success"),
        message: t("worklog.success.saved") || "Worklog saved",
      });

      setHours("");
      setMinutes("");
      setDescription("");
      setLabelId(null);
      closePopover?.();
    } catch (err) {
      const error = err as AxiosError<{ detail?: string }>;
      const message = error.response?.data?.detail || error.message || "Failed to save worklog";
      setToast({ type: TOAST_TYPE.ERROR, title: t("common.error.label"), message });
    } finally {
      setIsSaving(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>, close: () => void) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      // Use void to explicitly mark the floating promise
      void handleSave(close);
    }
  };

  return (
    <Popover
      className="relative"
      button={
        <Button variant="neutral-primary" size="sm" prependIcon={<Plus className="h-3 w-3" />} disabled={disabled}>
          {t("worklog.log_work") || "Log work"}
        </Button>
      }
    >
      {({ close }: { close: () => void }) => (
        <WorklogForm
          hours={hours}
          minutes={minutes}
          description={description}
          labelId={labelId}
          labelOptions={labelOptions}
          onLabelChange={setLabelId}
          showLabelSelect={shouldShowLabelSelect}
          onHoursChange={setHours}
          onMinutesChange={setMinutes}
          onDescriptionChange={setDescription}
          onSave={() => void handleSave(close)}
          onCancel={() => {
            setHours("");
            setMinutes("");
            setDescription("");
            setLabelId(null);
            close();
          }}
          isSaving={isSaving}
          saveButtonText={t("save") || "Save"}
          onKeyDown={(e) => handleKeyDown(e, close)}
        />
      )}
    </Popover>
  );
}
