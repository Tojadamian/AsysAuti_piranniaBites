import React from "react";

const MetricCard = ({ text = "Metric", onClick }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        width: "100%",
        padding: 18,
        background: "#e6e6e6",
        border: "none",
        borderRadius: 8,
        textAlign: "center",
        fontWeight: 600,
        color: "#222",
        cursor: "pointer",
      }}
    >
      {text}
    </button>
  );
};

export default MetricCard;
