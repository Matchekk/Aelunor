import React from "react";
import ReactDOM from "react-dom/client";

import { AppRoot } from "./app/AppRoot";
import "./shared/styles/globals.css";
import "./shared/styles/waiting.css";
import "./shared/styles/legacy/legacy-vars.css";
import "./shared/styles/legacy/legacy-shell.css";
import "./shared/styles/legacy/legacy-play.css";
import "./shared/styles/aelunor-main-screen.css";
import "./shared/styles/aelunor-play-shell.css";
import "./shared/styles/aelunor-play-composer.css";
import "./shared/styles/aelunor-play-shell-responsive.css";
import "./features/play/campaignPlayV2.css";
import "./shared/styles/font-semantics.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <AppRoot />
  </React.StrictMode>,
);
