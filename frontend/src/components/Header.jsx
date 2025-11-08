import React from "react";

const styles = {
  Header: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    height: "60px",
    backgroundColor: "#ffffff",
    borderBottom: "0.8px solid #e5e7eb",
    boxSizing: "border-box",
    display: "flex",
    alignItems: "center",
    zIndex: 60,
    paddingLeft: 12,
  },
};

const Header = (props) => {
  return <div style={styles.Header}>{props.children}</div>;
};

export default Header;
