import React from "react";

// Back arrow icon — replaced with the provided BackIcon implementation but
// adapted to accept common props (width, height, fill, style).
const IconFooterLeft = ({
  width = 28,
  height = 28,
  fill = "#030303",
  style = {},
  ...props
}) => {
  const combinedStyle = { width, height, ...style };
  return (
    <svg
      viewBox="0 0 24 24"
      style={combinedStyle}
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <path fill="none" d="M0 0h24v24H0z" />
      <path
        fill={fill}
        d="m9 19 1.41-1.41L5.83 13H22v-2H5.83l4.59-4.59L9 5l-7 7 7 7z"
      />
    </svg>
  );
};

export default IconFooterLeft;
