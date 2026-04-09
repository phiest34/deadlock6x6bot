(function () {
  "use strict";

  var statusElement = document.getElementById("bridge-status");

  function setStatus(message) {
    statusElement.textContent = message;
  }

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
