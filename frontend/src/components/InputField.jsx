import React, { useState } from "react";

const styles = {
  Input: {
    width: "100%",
    maxWidth: "335px",
    height: "48px",
    padding: "8px 12px",
    border: "1px solid #d3d3d8",
    borderRadius: "12px",
    backgroundColor: "#ffffff",
    color: "#333",
    fontSize: "14px",
    fontFamily: "Poppins, Arial, sans-serif",
    outline: "none",
    boxSizing: "border-box",
  },
};

const defaultProps = {
  text: "Wpisz swoje notatki tutaj...",
};



const InputField = ({ text, onChange }) => {
  const [value, setValue] = useState("");

  const handleChange = (e) => {
    const newValue = e.target.value;
    setValue(newValue);
    if (onChange) onChange(newValue); // send value to parent
  };

  return (
    <input
      style={styles.Input}
      placeholder={text ?? "Wpisz swoje notatki tutaj..."}
      value={value}
      onChange={handleChange}
    />
  );
};

export default InputField;

