// WorklogForm.tsx
import type { KeyboardEvent } from "react";
import { useRef, useState } from "react";
import { usePopper } from "react-popper";
import { Combobox } from "@headlessui/react";
import { Icon, CheckIcon, SearchIcon, ChevronDownIcon, LabelPropertyIcon } from "@plane/propel/icons";
import { useTranslation } from "@/hooks/use-translation";
import { ComboDropDown } from "@plane/ui";
import { useDropdown } from "@/hooks/use-dropdown";

// Define the type for the translation hook
type TTranslation = {
  t: (key: string, options?: Record<string, unknown>) => string;
};

interface WorklogFormProps {
  hours: string;
  minutes: string;
  description: string;
  labelId?: string | null;
  labelOptions?: { id: string; name: string; color?: string }[];
  onLabelChange?: (value: string | null) => void;
  showLabelSelect?: boolean;
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
    labelId,
    labelOptions = [],
    onLabelChange,
    showLabelSelect = false,
    onHoursChange,
    onMinutesChange,
    onDescriptionChange,
    onSave,
    onCancel,
    isSaving,
    saveButtonText = "Save",
    onKeyDown,
  } = props;

  // FIX: Cast to unknown then to the specific translation type
  const { t } = useTranslation() as unknown as TTranslation;

  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [referenceElement, setReferenceElement] = useState<HTMLButtonElement | null>(null);
  const [popperElement, setPopperElement] = useState<HTMLDivElement | null>(null);
  const { styles, attributes } = usePopper(referenceElement, popperElement, {
    placement: "bottom-start",
    modifiers: [
      {
        name: "preventOverflow",
        options: {
          padding: 12,
        },
      },
    ],
  });
  const { handleClose, handleKeyDown, handleOnClick, searchInputKeyDown } = useDropdown({
    dropdownRef,
    inputRef,
    isOpen,
    query,
    setIsOpen,
    setQuery,
  });
  const filteredOptions =
    query === ""
      ? labelOptions
      : labelOptions.filter((option) => option.name.toLowerCase().includes(query.toLowerCase()));
  const selectedLabel = labelOptions.find((option) => option.id === labelId);

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

      {showLabelSelect && labelOptions.length > 0 && (
        <ComboDropDown
          as="div"
          ref={dropdownRef}
          value={labelId ?? null}
          onChange={(val: string | null) => {
            onLabelChange?.(val);
            handleClose();
          }}
          onKeyDown={handleKeyDown}
          className="w-full"
          button={
            <button
              ref={setReferenceElement}
              type="button"
              className="clickable flex h-8 w-full items-center justify-between gap-2 rounded border border-custom-border-200 bg-custom-background-90 px-2 text-sm text-custom-text-100"
              onClick={handleOnClick}
            >
              <span className="flex items-center gap-2 truncate">
                <LabelPropertyIcon className="h-3.5 w-3.5 text-custom-text-300" />
                {selectedLabel ? (
                  <span className="flex items-center gap-2 truncate">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: selectedLabel.color }} />
                    <span className="truncate">{selectedLabel.name}</span>
                  </span>
                ) : (
                  <span className="text-placeholder">{t("common.select") || "Select label"}</span>
                )}
              </span>
              <ChevronDownIcon className="h-3 w-3 text-custom-text-300" />
            </button>
          }
        >
          {isOpen && (
            <Combobox.Options className="fixed z-10" static>
              <div
                className="my-1 w-48 rounded-sm border-[0.5px] border-strong bg-surface-1 px-2 py-2.5 text-11 shadow-raised-200 focus:outline-none"
                ref={setPopperElement}
                style={styles.popper}
                {...attributes.popper}
              >
                <div className="flex items-center gap-1.5 rounded-sm border border-subtle bg-surface-2 px-2">
                  <SearchIcon className="h-3.5 w-3.5 text-placeholder" strokeWidth={1.5} />
                  <Combobox.Input
                    ref={inputRef}
                    className="w-full bg-transparent py-1 text-11 text-secondary placeholder:text-placeholder focus:outline-none"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder={t("common.search.placeholder")}
                    displayValue={(value: string | null) => (value ? (selectedLabel?.name ?? "") : "")}
                    onKeyDown={searchInputKeyDown}
                  />
                </div>
                <div className="mt-2 max-h-48 space-y-1 overflow-y-scroll">
                  {filteredOptions.length > 0 ? (
                    filteredOptions.map((option) => (
                      <Combobox.Option key={option.id} value={option.id}>
                        {({ active, selected }) => (
                          <div
                            className={`flex w-full cursor-pointer select-none items-center justify-between gap-2 truncate rounded-sm px-1 py-1.5 ${
                              active ? "bg-layer-transparent-hover" : ""
                            } ${selected ? "text-primary" : "text-secondary"}`}
                          >
                            <span className="flex items-center gap-2 truncate">
                              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: option.color }} />
                              <span className="truncate">{option.name}</span>
                            </span>
                            {selected && <CheckIcon className="h-3.5 w-3.5 flex-shrink-0" />}
                          </div>
                        )}
                      </Combobox.Option>
                    ))
                  ) : (
                    <p className="px-1.5 py-1 italic text-placeholder">{t("common.search.no_matching_results")}</p>
                  )}
                </div>
              </div>
            </Combobox.Options>
          )}
        </ComboDropDown>
      )}

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
