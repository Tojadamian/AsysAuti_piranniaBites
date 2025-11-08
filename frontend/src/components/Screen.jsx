import React from "react";

/**
 * Screen - prosty kontener ekranowy dla aplikacji
 * Props:
 *  - children: React nodes
 *  - style: dodatkowy obiekt stylów, merge'owany z domyślnym
 *  - className: opcjonalna klasa CSS
 *  - padded: jeśli true -> doda wewnętrzny padding
 *  - center: jeśli true -> wyśrodkuje zawartość poziomo
 *  - backgroundColor: nadpisze tło (domyślnie #fff)
 *  - fullHeight: jeśli true -> minHeight: '100vh'
 *  - maxWidth: ogranicza szerokość wewnętrznego kontenera
 */

const Screen = ({
  children,
  style = {},
  className = "",
  padded = true,
  center = false,
  backgroundColor = "#ffffff",
  fullHeight = false,
  maxWidth = 1200,
}) => {
  const base = {
    backgroundColor,
    padding: padded ? 20 : 0,
    boxSizing: "border-box",
    display: "flex",
    flexDirection: "column",
    alignItems: center ? "center" : "stretch",
    justifyContent: center ? "center" : undefined,
    minHeight: fullHeight ? "100vh" : undefined,
    width: "100%",
  };

  const inner = {
    width: "100%",
    maxWidth: maxWidth,
    margin: "0 auto",
  };

  return (
    <div style={{ ...base, ...style }} className={className}>
      <div style={inner}>{children}</div>
    </div>
  );
};

export default Screen;
