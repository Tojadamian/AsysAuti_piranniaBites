import React from "react";

const styles = {
  Text: {
    color: "#030303",
    fontSize: "clamp(20px, 5vw, 48px)",
    fontFamily: "Poppins, Arial, sans-serif",
    fontWeight: 300,
    lineHeight: "1.1",
    textAlign: "center",
  },
};

const defaultProps = {
  text: "AsysAuti",
};

const Text = (props) => {
  return <div style={styles.Text}>{props.text ?? defaultProps.text}</div>;
};

export default Text;
