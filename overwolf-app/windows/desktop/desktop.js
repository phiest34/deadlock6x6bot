(function () {
  "use strict";

  var statusElement = document.getElementById("bridge-status");
  var titlebarElement = document.getElementById("titlebar");
  var minimizeButton = document.getElementById("minimize-button");
  var closeButton = document.getElementById("close-button");
  var currentWindowId = null;

  function setStatus(message) {
    statusElement.textContent = message;
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
