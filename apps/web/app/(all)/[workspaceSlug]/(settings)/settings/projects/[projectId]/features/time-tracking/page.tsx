/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/* eslint-disable react-refresh/only-export-components */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@/hooks/use-translation";
// components
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { ProjectSettingsFeatureControlItem } from "@/components/settings/project/content/feature-control-item";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
// local imports
import type { Route } from "./+types/page";
import { FeaturesTimeTrackingProjectSettingsHeader } from "./header";
import { SettingsHeading } from "@/components/settings/heading";

// Define the translation type outside the component for better readability
type TTranslation = {
  t: (key: string, options?: Record<string, unknown>) => string;
};

function FeaturesTimeTrackingSettingsPage({ params }: Route.ComponentProps) {
  const { workspaceSlug, projectId } = params;
  // store hooks
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  const { currentProjectDetails } = useProject();

  // Translation hook with double casting to bypass unsafe assignment rules
  const { t } = useTranslation() as unknown as TTranslation;

  // derived values
  const pageTitle = currentProjectDetails?.name
    ? `${currentProjectDetails?.name} settings - ${t("project_settings.features.time_tracking.short_title")}`
    : undefined;

  const canPerformProjectAdminActions = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);

  if (workspaceUserInfo && !canPerformProjectAdminActions) {
    return <NotAuthorizedView section="settings" isProjectView className="h-auto" />;
  }

  return (
    <SettingsContentWrapper header={<FeaturesTimeTrackingProjectSettingsHeader />}>
      <PageHead title={pageTitle} />
      <section className="w-full">
        <SettingsHeading
          title={t("project_settings.features.time_tracking.title")}
          description={t("project_settings.features.time_tracking.description")}
        />
        <div className="mt-7">
          <ProjectSettingsFeatureControlItem
            title={t("project_settings.features.time_tracking.toggle_title")}
            description={t("project_settings.features.time_tracking.toggle_description")}
            featureProperty="is_time_tracking_enabled"
            projectId={projectId}
            value={!!currentProjectDetails?.is_time_tracking_enabled}
            workspaceSlug={workspaceSlug}
          />
        </div>
      </section>
    </SettingsContentWrapper>
  );
}

export default observer(FeaturesTimeTrackingSettingsPage);
