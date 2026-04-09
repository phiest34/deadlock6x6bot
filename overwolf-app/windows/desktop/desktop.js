(function () {
  "use strict";

  var statusElement = document.getElementById("bridge-status");
  var titlebarElement = document.getElementById("titlebar");
  var minimizeButton = document.getElementById("minimize-button");
  var closeButton = document.getElementById("close-button");
  var currentWindowId = null;
  var debugFields = {
    runningGameInfo: document.getElementById("running-game-info"),
    requestedFeatures: document.getElementById("requested-features"),
    lastGameInfoUpdate: document.getElementById("game-info-updated"),
    lastInfoUpdate: document.getElementById("info-update"),
    lastNewEvents: document.getElementById("new-events"),
    lastSnapshot: document.getElementById("last-snapshot"),
    lastBridgeError: document.getElementById("bridge-error")
  };

  function setStatus(message) {
    statusElement.textContent = message;
  }

  function stringify(value) {
    if (!value) {
      return "No data yet.";
    }

    try {
      return JSON.stringify(value, null, 2);
    } catch (_error) {
      return String(value);
    }
  }

  function renderDebugState(payload) {
    Object.keys(debugFields).forEach(function (key) {
      if (!debugFields[key]) {
        return;
      }

      debugFields[key].textContent = stringify(payload[key]);
    });
  }

  function pollMainWindowState() {
    if (!window.overwolf || !overwolf.windows || typeof overwolf.windows.getMainWindow !== "function") {
      return;
    }

    var mainWindow = overwolf.windows.getMainWindow();
    if (!mainWindow || !mainWindow.deadbotDebugState) {
      return;
    }

    renderDebugState(mainWindow.deadbotDebugState);
  }

  function bindWindowControls() {
    if (!window.overwolf || !overwolf.windows) {
      return;
    }

    overwolf.windows.getCurrentWindow(function (result) {
      if (!result.success || !result.window) {
        return;
      }

      currentWindowId = result.window.id;
    });

    titlebarElement.addEventListener("mousedown", function (event) {
      if (!currentWindowId) {
        return;
      }

      if (event.target && event.target.closest("button")) {
        return;
      }

      overwolf.windows.dragMove(currentWindowId);
    });

    minimizeButton.addEventListener("click", function () {
      if (!currentWindowId) {
        return;
      }

      overwolf.windows.minimize(currentWindowId);
    });

    closeButton.addEventListener("click", function () {
      if (!currentWindowId) {
        return;
      }

      overwolf.windows.close(currentWindowId);
    });
  }

  bindWindowControls();
  pollMainWindowState();
  window.setInterval(pollMainWindowState, 1000);

  fetch("http://127.0.0.1:8765/health")
    .then(function (response) {
      if (!response.ok) {
        throw new Error("Bridge health request failed");
      }
      return response.json();
    })
    .then(function (payload) {
      setStatus("Bridge is healthy. Stored events: " + payload.events_received);
    })
    .catch(function () {
      setStatus("Bridge is offline. Start bridge/server.py before testing.");
    });
})();
