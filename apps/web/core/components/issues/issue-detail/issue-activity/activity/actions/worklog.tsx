import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { Network } from "lucide-react";
import { Icon } from "@plane/propel/icons";
import { Tooltip } from "@plane/propel/tooltip";
import { renderFormattedTime, renderFormattedDate, calculateTimeAgo } from "@plane/utils";
import { usePlatformOS } from "@/hooks/use-platform-os";
import { WorklogQuickActions } from "./helpers/worklog";

// Define proper types for the worklog data
interface ActorDetail {
  display_name?: string;
}

interface Worklog {
  id: string;
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
};

export function WorklogBlockComponent(props: TWorklogBlockComponent) {
  const { icon, worklog, ends, inlineText, descriptionBlock, quickActions } = props;
  const { isMobile } = usePlatformOS();

  if (!worklog) return null;

  return (
    <div className={`relative flex gap-3 ${ends === "top" ? `pb-2` : ends === "bottom" ? `pt-2` : `py-2`}`}>
      <div className="absolute left-[13px] top-0 bottom-0 w-0.5 bg-custom-background-80" aria-hidden />
      <div className="flex-shrink-0 ring-6 w-7 h-7 rounded-full overflow-hidden flex justify-center items-center z-[4] bg-custom-background-80 text-custom-text-200">
        {icon ? icon : <Network className="w-3.5 h-3.5" />}
      </div>

      {descriptionBlock ? (
        // Layout con descripción (como comentario)
        <div className="flex flex-col gap-3 flex-grow">
          <div className="flex w-full gap-2">
            <div className="flex-1 flex flex-wrap items-center gap-1">
              <span className="text-xs font-medium">{worklog.actor_detail?.display_name || "User"}</span>
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
        // Layout simple (una línea)
        <div className="w-full flex items-start justify-between gap-2">
          <div className="flex-1 text-custom-text-200 text-xs">
            <span className="text-custom-text-100 font-medium">{worklog.actor_detail?.display_name || "User"}</span>
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

  if (!activityComment) return null;

  const hours = Math.floor(activityComment.duration / 60);
  const minutes = activityComment.duration % 60;

  const handleEdit = () => {
    console.log("Edit worklog:", activityComment.id);
  };

  const handleDelete = () => {
    if (window.confirm("Are you sure you want to delete this worklog?")) {
      console.log("Delete worklog:", activityComment.id);
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
      <WorklogBlockComponent
        worklog={activityComment}
        icon={<Icon name="project.clock" className="h-3 w-3 text-custom-text-200" />}
        ends={ends}
        inlineText={timeLoggedText}
        descriptionBlock={
          <div className="text-base bg-custom-background-100 rounded border border-custom-border-200 p-3">
            {activityComment.description}
          </div>
        }
        quickActions={<WorklogQuickActions worklog={activityComment} onEdit={handleEdit} onDelete={handleDelete} />}
      />
    );
  }

  return (
    <WorklogBlockComponent
      worklog={activityComment}
      icon={<Icon name="project.clock" className="h-3 w-3 text-custom-text-200" />}
      ends={ends}
      inlineText={timeLoggedText}
      quickActions={<WorklogQuickActions worklog={activityComment} onEdit={handleEdit} onDelete={handleDelete} />}
    />
  );
});
