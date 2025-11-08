import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import Screen from "./components/Screen";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {/* Screen jest teraz globalnym wrapperem dla całej aplikacji */}
    <Screen
      padded={true}
      center={true}
      fullHeight={true}
      backgroundColor="#f8fbff"
    >
      <App />
    </Screen>
  </React.StrictMode>
);
