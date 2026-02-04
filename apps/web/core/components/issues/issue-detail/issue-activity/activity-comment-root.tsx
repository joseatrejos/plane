/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import type { E_SORT_ORDER, TActivityFilters, EActivityFilterType } from "@plane/constants";
import { BASE_ACTIVITY_FILTER_TYPES, filterActivityOnSelectedFilters } from "@plane/constants";
import type { TCommentsOperations } from "@plane/types";
// components
import { CommentCard } from "@/components/comments/card/root";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// plane web components
import { IssueAdditionalPropertiesActivity } from "@/plane-web/components/issues/issue-details/issue-properties-activity";
import { IssueActivityWorklog } from "./activity/actions/worklog";
// local imports
import { IssueActivityItem } from "./activity/activity-list";
import { IssueActivityLoader } from "./loader";

type TIssueActivityCommentRoot = {
  workspaceSlug: string;
  projectId: string;
  isIntakeIssue: boolean;
  issueId: string;
  selectedFilters: TActivityFilters[];
  activityOperations: TCommentsOperations;
  showAccessSpecifier?: boolean;
  disabled?: boolean;
  sortOrder: E_SORT_ORDER;
};

export const IssueActivityCommentRoot = observer(function IssueActivityCommentRoot(props: TIssueActivityCommentRoot) {
  const {
    workspaceSlug,
    isIntakeIssue,
    issueId,
    selectedFilters,
    activityOperations,
    showAccessSpecifier,
    projectId,
    disabled,
    sortOrder,
  } = props;
  // store hooks
  const {
    activity: { getActivityAndCommentsByIssueId, getWorklogById },
    comment: { getCommentById },
  } = useIssueDetail();
  // derived values
  const activityAndComments = getActivityAndCommentsByIssueId(issueId, sortOrder);

  if (!activityAndComments) return <IssueActivityLoader />;

  if (activityAndComments.length <= 0) return null;

  const filteredActivityAndComments = filterActivityOnSelectedFilters(activityAndComments, selectedFilters);

  return (
    <div>
      {filteredActivityAndComments.map((activityComment, index) => {
        if (activityComment.activity_type === "WORKLOG") {
          const worklog = getWorklogById(activityComment.id);
          return (
            <IssueActivityWorklog
              key={activityComment.id}
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              issueId={issueId}
              activityComment={worklog ?? activityComment}
              ends={index === 0 ? "top" : index === filteredActivityAndComments.length - 1 ? "bottom" : undefined}
            />
          );
        }

        if (activityComment.activity_type === "COMMENT") {
          const comment = getCommentById(activityComment.id);

          return (
            <CommentCard
              key={activityComment.id}
              workspaceSlug={workspaceSlug}
              comment={comment}
              activityOperations={activityOperations}
              ends={index === 0 ? "top" : index === filteredActivityAndComments.length - 1 ? "bottom" : undefined}
              showAccessSpecifier={!!showAccessSpecifier}
              showCopyLinkOption={!isIntakeIssue}
              disabled={disabled}
              projectId={projectId}
            />
          );
        }

        if (BASE_ACTIVITY_FILTER_TYPES.includes(activityComment.activity_type as EActivityFilterType)) {
          return (
            <IssueActivityItem
              key={activityComment.id}
              activityId={activityComment.id}
              ends={index === 0 ? "top" : index === filteredActivityAndComments.length - 1 ? "bottom" : undefined}
            />
          );
        }

        if (activityComment.activity_type === "ISSUE_ADDITIONAL_PROPERTIES_ACTIVITY") {
          return (
            <IssueAdditionalPropertiesActivity
              key={activityComment.id}
              activityId={activityComment.id}
              ends={index === 0 ? "top" : index === filteredActivityAndComments.length - 1 ? "bottom" : undefined}
            />
          );
        }

        return null;
      })}
    </div>
  );
});
