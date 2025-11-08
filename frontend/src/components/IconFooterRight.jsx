import React from "react";

const IconFooterRight = ({
  width = 28,
  height = 28,
  fill = "#030303",
  style = {},
  ...props
}) => {
  const combined = { width, height, ...style };
  return (
    <svg
      viewBox="0 0 24 24"
      style={combined}
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <path d="M0 0h24v24H0z" fill="none" />
      <path
        fill={fill}
        d="M19 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h4l3 3 3-3h4c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-5.12 10.88L12 17l-1.88-4.12L6 11l4.12-1.88L12 5l1.88 4.12L18 11l-4.12 1.88z"
      />
    </svg>
  );
};

export default IconFooterRight;
