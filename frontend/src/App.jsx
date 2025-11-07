import React from "react";
import ParticipantViewer from "./components/ParticipantViewer";

export default function App() {
  return (
    <div style={{ fontFamily: "Arial, sans-serif", padding: 20 }}>
      <h1>AsysAuti — Viewer</h1>
      <p>Prosty interfejs do podglądu uczestników z backendu.</p>
      <ParticipantViewer />
    </div>
  );
}
