import React from "react";

const MonitoringItem = ({ title, img, onClick, isHighlighted = false }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        backgroundColor: "#e9e9e9",
        padding: 16,
        borderRadius: 12,
        boxShadow: "none",
        border: "none",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 12,
        cursor: "pointer",
        minHeight: 120,
        justifyContent: "center",
        ...(isHighlighted
          ? { boxShadow: "0 0 0 2px rgba(59,130,246,0.12)" }
          : {}),
      }}
    >
      <div style={{ textAlign: "center", fontWeight: 700, fontSize: 14 }}>
        {title}
      </div>

      <div
        style={{
          width: "100%",
          height: 92,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <img
          src={img}
          alt={title}
          style={{
            maxHeight: "92px",
            maxWidth: "70%",
            objectFit: "contain",
            display: "block",
          }}
        />
      </div>
    </button>
  );
};

export default MonitoringItem;
