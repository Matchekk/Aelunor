import { useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { clearSessionBootstrap, readSessionBootstrap, type SessionBootstrap } from "./bootstrap/sessionStorage";
import { ErrorBoundary } from "./errors/ErrorBoundary";
import { QueryProvider } from "./providers/QueryProvider";
import { ThemeProvider } from "./providers/ThemeProvider";
import { RouteGate } from "./routing/RouteGate";

function AppWorkspace() {
  const [activeSession, setActiveSession] = useState<SessionBootstrap>(() => readSessionBootstrap());

  const clearActiveSession = () => {
    clearSessionBootstrap();
    setActiveSession(readSessionBootstrap());
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/v1/*"
          element={
            <RouteGate
              active_session={activeSession}
              on_active_session_change={setActiveSession}
              on_clear_active_session={clearActiveSession}
            />
          }
        />
        <Route path="*" element={<Navigate to="/v1" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export function AppRoot() {
  return (
    <ErrorBoundary>
      <QueryProvider>
        <ThemeProvider>
          <AppWorkspace />
        </ThemeProvider>
      </QueryProvider>
    </ErrorBoundary>
  );
}
