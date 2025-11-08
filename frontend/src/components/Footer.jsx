import React from "react";
import IconFooterLeft from "./IconFooterLeft";
import IconFooterMiddle from "./IconFooterMiddle";
import IconFooterRight from "./IconFooterRight";

const styles = {
  footer: {
    position: "fixed",
    left: 0,
    right: 0,
    bottom: 0,
    height: 64,
    backgroundColor: "#ffffff",
    display: "flex",
    justifyContent: "space-around",
    alignItems: "center",
    boxShadow: "0 -2px 8px rgba(3,3,3,0.08)",
    zIndex: 40,
  },
  link: {
    textDecoration: "none",
    color: "#333",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: 60,
    height: 60,
    borderRadius: 12,
  },
};

const Footer = () => {
  return (
    <div style={styles.footer}>
      {/* left: go back */}
      <button
        type="button"
        onClick={() => window.history.back()}
        style={{ ...styles.link, border: "none", background: "transparent" }}
        aria-label="Cofnij"
      >
        <IconFooterLeft width={28} height={28} />
      </button>

      {/* middle: unchanged (keeps linking to dashboard/home) */}
      <a href="#/dashboard" style={styles.link} aria-label="Home">
        <IconFooterMiddle width={28} height={28} />
      </a>

      {/* right: go to AI assistant (viewer) */}
      <a href="#/chat" style={styles.link} aria-label="AsysChat">
        <IconFooterRight width={28} height={28} />
      </a>
    </div>
  );
};

export default Footer;
