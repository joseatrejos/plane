import { observer } from "mobx-react";
import React from "react"; // Added to use React.FC or React.ElementType
// plane imports
import { PROJECT_SETTINGS } from "@plane/constants";
import { useTranslation } from "@/hooks/use-translation";
import { Breadcrumbs } from "@plane/ui";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { SettingsPageHeader } from "@/components/settings/page-header";
import { PROJECT_SETTINGS_ICONS } from "@/components/settings/project/sidebar/item-icon";

export const FeaturesTimeTrackingProjectSettingsHeader = observer(function FeaturesTimeTrackingProjectSettingsHeader() {
  // translation
  const { t } = useTranslation() as {
    t: (key: string, options?: Record<string, unknown>) => string;
  };

  // derived values
  const settingsDetails = PROJECT_SETTINGS.features_time_tracking;

  const Icon = PROJECT_SETTINGS_ICONS.features_time_tracking as React.ComponentType<unknown>;

  return (
    <SettingsPageHeader
      leftItem={
        <div className="flex items-center gap-2">
          <Breadcrumbs>
            <Breadcrumbs.Item
              component={
                <BreadcrumbLink
                  label={t(settingsDetails.i18n_label)}
                  icon={<Icon className="size-4 text-tertiary" />}
                />
              }
            />
          </Breadcrumbs>
        </div>
      }
    />
  );
});
