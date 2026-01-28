import { useState, KeyboardEvent } from "react";
import { Plus } from "lucide-react";
import axios, { AxiosError } from "axios";
// plane imports
import { Button } from "@plane/propel/button";
import { Popover } from "@plane/ui";
import { useTranslation } from "@plane/i18n";
import { Icon } from "@plane/propel/icons";
import { API_BASE_URL } from "@plane/constants";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";

type Props = {
  workspaceSlug?: string;
  projectId?: string;
  issueId?: string;
  disabled?: boolean;
};

export function IssueActivityWorklogCreateButton(props: Props) {
  const { disabled, workspaceSlug, projectId, issueId } = props;
  const { t } = useTranslation();

  const [hours, setHours] = useState<string>("");
  const [minutes, setMinutes] = useState<string>("");
  const [description, setDescription] = useState("");
  const [isSaving, setIsSaving] = useState(false);

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
        message: t("please_add_duration") || "Please add a duration",
      });
      return;
    }

    setIsSaving(true);
    const url = `${API_BASE_URL}/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/worklogs/`;

    try {
      const payload = { duration, description };
      await axios.post(url, payload, { withCredentials: true });

      window.dispatchEvent(new CustomEvent("worklog_updated"));

      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("success"),
        message: t("worklog_success_saved") || "Worklog saved",
      });

      setHours("");
      setMinutes("");
      setDescription("");
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
          {t("log_work") || "Log work"}
        </Button>
      }
    >
      {({ close }: { close: () => void }) => (
        <div
          role="presentation"
          className="w-80 p-4 bg-custom-background-100 border border-custom-border-200 rounded-md shadow-lg space-y-4 outline-none"
          onKeyDown={(e) => handleKeyDown(e, close)}
        >
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-custom-background-80 rounded-full border border-custom-border-200">
              <Icon name="project.clock" className="h-3 w-3 text-custom-text-300" />
              <span className="text-[11px] font-medium text-custom-text-200">
                {hours || 0}h {minutes || 0}m
              </span>
            </div>
          </div>

          <div className="flex gap-2">
            <input
              type="number"
              placeholder="Hours"
              value={hours}
              onChange={(e) => setHours(e.target.value)}
              className="w-full bg-custom-background-90 border border-custom-border-200 rounded px-2 py-1 text-sm outline-none focus:border-custom-primary-100 text-custom-text-100"
            />
            <input
              type="number"
              placeholder="Minutes"
              value={minutes}
              onChange={(e) => setMinutes(e.target.value)}
              className="w-full bg-custom-background-90 border border-custom-border-200 rounded px-2 py-1 text-sm outline-none focus:border-custom-primary-100 text-custom-text-100"
            />
          </div>

          <textarea
            placeholder="Description..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full bg-custom-background-90 border border-custom-border-200 rounded p-2 text-sm min-h-[80px] outline-none focus:border-custom-primary-100 text-custom-text-100 resize-none"
          />

          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="px-3 py-1 text-sm text-custom-text-200 hover:bg-custom-background-80 rounded transition-colors"
              onClick={() => {
                setHours("");
                setMinutes("");
                setDescription("");
                close();
              }}
              disabled={isSaving}
            >
              {t("cancel") || "Cancel"}
            </button>
            <button
              type="button"
              className="px-4 py-1 text-sm bg-custom-primary-100 text-white rounded hover:bg-custom-primary-200 transition-colors font-medium"
              onClick={() => {
                void handleSave(close);
              }}
              disabled={isSaving}
            >
              {isSaving ? t("save") || "Saving..." : t("save") || "Save"}
            </button>
          </div>
        </div>
      )}
    </Popover>
  );
}
