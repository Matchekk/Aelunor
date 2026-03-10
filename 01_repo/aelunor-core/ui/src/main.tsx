import React from "react";
import ReactDOM from "react-dom/client";

import { AppRoot } from "./app/AppRoot";
import "./shared/styles/globals.css";
import "./shared/styles/legacy/legacy-vars.css";
import "./shared/styles/legacy/legacy-shell.css";
import "./shared/styles/legacy/legacy-play.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <AppRoot />
  </React.StrictMode>,
);
