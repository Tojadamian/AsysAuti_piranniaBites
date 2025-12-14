import React, { useEffect, useState } from "react";
import ParticipantViewer from "./components/ParticipantViewer";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import MonitoringPanel from "./pages/MonitoringPanel";
import Chat from "./pages/Chat";
import BarometrStresu from "./pages/BarometrStresu";
import Profile from "./pages/Profile";

export default function App() {
  // Simple reactive router using hash for navigation
  const getRoute = () => {
    if (typeof window === "undefined") return "/";
    const hash = window.location.hash || "";
    if (hash && hash.length > 1) return hash.replace(/^#/, "");
    const path = window.location.pathname || "/";
    return path.startsWith("/") ? path : "/" + path;
  };

  const [route, setRoute] = useState(getRoute);

  useEffect(() => {
    const onHashChange = () => setRoute(getRoute());
    window.addEventListener("hashchange", onHashChange);
    window.addEventListener("popstate", onHashChange);
    setRoute(getRoute());
    
    return () => {
      window.removeEventListener("hashchange", onHashChange);
      window.removeEventListener("popstate", onHashChange);
    };
  }, []);

  // Route components
  const routes = {
    "/viewer": (
      <div style={{ fontFamily: "Arial, sans-serif", padding: 6 }}>
        <h1>AsysAuti — Viewer</h1>
        <p>Prosty interfejs do podglądu uczestników z backendu.</p>
        <ParticipantViewer />
      </div>
    ),
    "/login": (
      <div style={{ fontFamily: "Arial, sans-serif", padding: 6 }}>
        <h1>AsysAuti — Logowanie</h1>
        <Login />
      </div>
    ),
    "/dashboard": (
      <div style={{ fontFamily: "Arial, sans-serif", padding: 6 }}>
        <Dashboard />
      </div>
    ),
    "/barometr-stresu": (
      <div style={{ fontFamily: "Arial, sans-serif", padding: 6 }}>
        <BarometrStresu />
      </div>
    ),
    "/monitoring": (
      <div style={{ fontFamily: "Arial, sans-serif", padding: 6 }}>
        <MonitoringPanel />
      </div>
    ),
    "/profile": (
      <div style={{ fontFamily: "Arial, sans-serif", padding: 6 }}>
        <Profile />
      </div>
    ),
    "/chat": (
      <div style={{ fontFamily: "Arial, sans-serif", padding: 6 }}>
        <Chat />
      </div>
    ),
  };

  // Find matching route
  for (const [routePath, component] of Object.entries(routes)) {
    if (route.startsWith(routePath)) {
      return component;
    }
  }

  return <Home />;
}
