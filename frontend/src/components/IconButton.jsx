import React from "react";

const IconButton = ({ children, onClick, ariaLabel = "icon-button", style = {} }) => {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      onClick={onClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        border: "none",
        background: "#fff",
        padding: 8,
        borderRadius: 8,
        boxShadow: "0 2px 6px rgba(0,0,0,0.06)",
        cursor: "pointer",
        ...style,
      }}
    >
      {children}
    </button>
  );
};

export default IconButton;
