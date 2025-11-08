import React, { useEffect, useState } from "react";
import ParticipantViewer from "./components/ParticipantViewer";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import MonitoringPanel from "./pages/MonitoringPanel";
import Chat from "./pages/Chat";
import BarometrStresu from "./pages/BarometrStresu";

export default function App() {
  // Prosty, reaktywny router: preferujemy hash (#/path), ale jeśli go nie ma
  // obsłużymy też bezpośrednie ścieżki (location.pathname) — to pozwala otwierać
  // stronę pod /chat bez konieczności używania hasha.
  const getRoute = () => {
    if (typeof window === "undefined") return "/";
    const hash = window.location.hash || "";
    if (hash && hash.length > 1) return hash.replace(/^#/, "");
    // brak hasha — użyjemy pathname (np. /chat). Upewnij się, że zaczyna od '/'.
    const path = window.location.pathname || "/";
    return path.startsWith("/") ? path : "/" + path;
  };

  const [route, setRoute] = useState(getRoute);

  useEffect(() => {
    const onHashChange = () => setRoute(getRoute());
    window.addEventListener("hashchange", onHashChange);
    // jeśli ktoś nawigował używając historii (pathname), reaguj też na popstate
    window.addEventListener("popstate", onHashChange);
    // też ustaw na montaż — przydatne podczas hot-reload lub bezpośredniego wejścia z hashem
    setRoute(getRoute());
    return () => {
      window.removeEventListener("hashchange", onHashChange);
      window.removeEventListener("popstate", onHashChange);
    };
  }, []);

  if (route.startsWith("/viewer")) {
    return (
      <div style={{ fontFamily: "Arial, sans-serif", padding: 6 }}>
        <h1>AsysAuti — Viewer</h1>
        <p>Prosty interfejs do podglądu uczestników z backendu.</p>
        <ParticipantViewer />
      </div>
    );
  }

  if (route.startsWith("/login")) {
    return (
      <div style={{ fontFamily: "Arial, sans-serif", padding: 6 }}>
        <h1>AsysAuti — Logowanie</h1>
        <Login />
      </div>
    );
  }

  if (route.startsWith("/dashboard")) {
    return (
      <div style={{ fontFamily: "Arial, sans-serif", padding: 6 }}>
        <Dashboard />
      </div>
    );
  }

  if (route.startsWith("/barometr-stresu")) {
    return (
      <div style={{ fontFamily: "Arial, sans-serif", padding: 6 }}>
        <BarometrStresu />
      </div>
    );
  }

  if (route.startsWith("/monitoring")) {
    return (
      <div style={{ fontFamily: "Arial, sans-serif", padding: 6 }}>
        <MonitoringPanel />
      </div>
    );
  }

  if (route.startsWith("/chat")) {
    return (
      <div style={{ fontFamily: "Arial, sans-serif", padding: 6 }}>
        <Chat />
      </div>
    );
  }

  return <Home />;
}
