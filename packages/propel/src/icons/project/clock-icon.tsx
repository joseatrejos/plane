import * as React from "react";
import { IconWrapper } from "../icon-wrapper"; // Asegúrate de que esta ruta sea correcta
import type { ISvgIcons } from "../type";

export function ClockIcon({ color = "currentColor", ...rest }: ISvgIcons) {
  const clipPathId = React.useId();
  return (
    <IconWrapper color={color} clipPathId={clipPathId} {...rest}>
      <path
        d="M8 1.5C4.41015 1.5 1.5 4.41015 1.5 8C1.5 11.5899 4.41015 14.5 8 14.5C11.5899 14.5 14.5 11.5899 14.5 8C14.5 4.41015 11.5899 1.5 8 1.5ZM0.25 8C0.25 3.71979 3.71979 0.25 8 0.25C12.2802 0.25 15.75 3.71979 15.75 8C15.75 12.2802 12.2802 15.75 8 15.75C3.71979 15.75 0.25 12.2802 0.25 8ZM8.625 4.25V8.25H12.125V9.5H7.375V4.25H8.625Z"
        fill={color}
      />
    </IconWrapper>
  );
}
