import { observer } from "mobx-react";
import { CustomMenu } from "@plane/ui";
import { Icon } from "@plane/propel/icons";

type TWorklogQuickActions = {
  onEdit: () => void;
  onDelete: () => void;
};

export const WorklogQuickActions = observer(function WorklogQuickActions(props: TWorklogQuickActions) {
  const { onEdit, onDelete } = props;

  return (
    <div className="opacity-0 group-hover:opacity-100 transition-opacity">
      <CustomMenu ellipsis placement="bottom-end" closeOnSelect>
        <CustomMenu.MenuItem onClick={onEdit}>
          <div className="flex items-center gap-2">
            <Icon name="pencil" className="h-3 w-3" />
            <span>Edit</span>
          </div>
        </CustomMenu.MenuItem>

        <CustomMenu.MenuItem onClick={onDelete}>
          <div className="flex items-center gap-2 text-red-500">
            <Icon name="trash" className="h-3 w-3" />
            <span>Delete</span>
          </div>
        </CustomMenu.MenuItem>
      </CustomMenu>
    </div>
  );
});
