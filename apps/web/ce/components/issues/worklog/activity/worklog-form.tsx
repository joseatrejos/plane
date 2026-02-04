// WorklogForm.tsx
import type { KeyboardEvent } from "react";
import { Icon } from "@plane/propel/icons";
import { useTranslation } from "@plane/i18n";

interface WorklogFormProps {
  hours: string;
  minutes: string;
  description: string;
  onHoursChange: (value: string) => void;
  onMinutesChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onSave: () => void;
  onCancel: () => void;
  isSaving: boolean;
  saveButtonText?: string;
  onKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
}

export function WorklogForm(props: WorklogFormProps) {
  const {
    hours,
    minutes,
    description,
    onHoursChange,
    onMinutesChange,
    onDescriptionChange,
    onSave,
    onCancel,
    isSaving,
    saveButtonText = "Save",
    onKeyDown,
  } = props;
  const { t } = useTranslation();

  return (
    <div
      role="presentation"
      className="w-80 p-4 bg-surface-2 rounded-md shadow-lg space-y-4 outline-none"
      onKeyDown={onKeyDown}
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
          onChange={(e) => onHoursChange(e.target.value)}
          className="w-full bg-custom-background-90 border border-custom-border-200 rounded px-2 py-1 text-sm outline-none focus:border-custom-primary-100 text-custom-text-100"
        />
        <input
          type="number"
          placeholder="Minutes"
          value={minutes}
          onChange={(e) => onMinutesChange(e.target.value)}
          className="w-full bg-custom-background-90 border border-custom-border-200 rounded px-2 py-1 text-sm outline-none focus:border-custom-primary-100 text-custom-text-100"
        />
      </div>

      <textarea
        placeholder="Description..."
        value={description}
        onChange={(e) => onDescriptionChange(e.target.value)}
        className="w-full bg-custom-background-90 border border-custom-border-200 rounded p-2 text-sm min-h-[80px] outline-none focus:border-custom-primary-100 text-custom-text-100 resize-none"
      />

      <div className="flex justify-end gap-2">
        <button
          type="button"
          className="px-3 py-1 text-sm text-custom-text-200 hover:bg-custom-background-80 rounded transition-colors"
          onClick={onCancel}
          disabled={isSaving}
        >
          {t("cancel") || "Cancel"}
        </button>
        <button
          type="button"
          className="px-4 py-1 text-sm bg-accent-primary text-white rounded hover:bg-custom-primary-200 transition-colors font-medium"
          onClick={onSave}
          disabled={isSaving}
        >
          {isSaving ? t("saving") || "Saving..." : saveButtonText}
        </button>
      </div>
    </div>
  );
}
