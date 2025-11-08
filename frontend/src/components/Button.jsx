import React from "react";

const styles = {
  Button: {
    cursor: "pointer",
    top: "549px",
    left: "24px",
    width: "100%",
    maxWidth: 340,
    height: 48,
    padding: "0px 12px",
    border: "0",
    boxSizing: "border-box",
    borderRadius: 12,
    backgroundColor: "#29b433",
    color: "#ffffff",
    fontSize: "16px",
    fontFamily: "Poppins, Arial, sans-serif",
    fontWeight: 500,
    lineHeight: "20px",
    outline: "none",
  },
};

const defaultProps = {
  label: "Start",
};

const Button = (props) => {
  const { onClick, label, style = {}, type = "button" } = props;
  return (
    <button
      type={type}
      onClick={onClick}
      style={{ ...styles.Button, ...style }}
    >
      {label ?? defaultProps.label}
    </button>
  );
};

export default Button;
