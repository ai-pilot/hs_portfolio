import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/chat.css";

const MOUNT_ID = "orient-express-root";

function mount() {
  let container = document.getElementById(MOUNT_ID);
  if (!container) {
    container = document.createElement("div");
    container.id = MOUNT_ID;
    document.body.appendChild(container);
  }
  const root = ReactDOM.createRoot(container);
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mount);
} else {
  mount();
}
