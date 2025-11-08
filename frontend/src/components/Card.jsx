import React from "react";

const styles = {
  Card: {
    width: "100%",
    backgroundColor: "#ffffff",
    borderRadius: 12,
    boxSizing: "border-box",
  },
};

const Card = (props) => {
  const { style = {}, children } = props;
  return <div style={{ ...styles.Card, ...style }}>{children}</div>;
};

export default Card;
