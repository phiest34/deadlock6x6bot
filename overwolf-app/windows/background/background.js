(function () {
  "use strict";

  var REQUIRED_FEATURES = ["game_info", "match_info"];
  var BRIDGE_BASE_URL = "http://127.0.0.1:8765";
  var state = {
    phase: null,
    gameMode: null,
    matchId: null,
    steamId: null,
    teamScore: null,
    roster: [],
    items: [],
    timerStartedAt: null,
    lastEvent: null
  };

  function log(message, data) {
    if (typeof data === "undefined") {
      console.log("[deadbot]", message);
      return;
    }

    console.log("[deadbot]", message, data);
  }

  function sendToOverlay(message) {
    overwolf.windows.obtainDeclaredWindow("overlay", function (result) {
      if (!result.success || !result.window) {
        return;
      }

      result.window.postMessage(
        {
          type: "deadbot.snapshot",
          snapshot: message
        },
        "*"
      );
    });
  }

  function withOverlayWindow(callback) {
    overwolf.windows.obtainDeclaredWindow("overlay", function (result) {
      if (!result.success || !result.window) {
        return;
      }

      callback(result.window.id);
    });
  }

  function postJson(path, payload) {
    return fetch(BRIDGE_BASE_URL + path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    }).catch(function (error) {
      log("Bridge request failed", error);
    });
  }

  function restoreDeclaredWindow(name) {
    overwolf.windows.obtainDeclaredWindow(name, function (result) {
      if (!result.success || !result.window) {
        log("Failed to obtain window", { name: name, result: result });
        return;
      }

      overwolf.windows.restore(result.window.id, function (restoreResult) {
        log("Restore window result", { name: name, result: restoreResult });
      });
    });
  }

  function emitSnapshot() {
    var snapshot = window.deadlockEvents.buildSnapshot(state);
    sendToOverlay(snapshot);
    postJson("/snapshot", snapshot);
  }

  function markTimerStartIfNeeded() {
    if (!state.timerStartedAt && state.phase === "GameInProgress") {
      state.timerStartedAt = Date.now();
    }
  }

  function applyInfoUpdates(infoUpdates) {
    var normalized = window.deadlockEvents.normalizeInfoUpdates(infoUpdates);

    if (normalized.phase) {
      state.phase = normalized.phase;
    }
    if (normalized.gameMode) {
      state.gameMode = normalized.gameMode;
    }
    if (normalized.matchId) {
      state.matchId = normalized.matchId;
    }
    if (normalized.steamId) {
      state.steamId = normalized.steamId;
    }
    if (normalized.teamScore) {
      state.teamScore = normalized.teamScore;
    }
    if (Array.isArray(normalized.roster)) {
      state.roster = normalized.roster;
    }
    if (Array.isArray(normalized.items)) {
      state.items = normalized.items;
    }

    markTimerStartIfNeeded();
    emitSnapshot();
  }

  function handleGameEvent(eventName, eventData) {
    if (eventName === "match_start") {
      state.timerStartedAt = Date.now();
    }

    if (eventName === "match_end") {
      state.lastEvent = {
        name: eventName,
        payload: eventData
      };
    }

    var eventPayload = window.deadlockEvents.normalizeGameEvent(eventName, eventData);
    state.lastEvent = eventPayload;
    postJson("/events", eventPayload);
    emitSnapshot();
  }

  function registerHotkey() {
    overwolf.settings.registerHotKey("toggle_overlay", function () {
      withOverlayWindow(function (windowId) {
        overwolf.windows.getWindowState(windowId, function (stateResult) {
          if (!stateResult.success) {
            return;
          }

          if (stateResult.window_state === "hidden") {
            overwolf.windows.restore(windowId);
          } else {
            overwolf.windows.hide(windowId);
          }
        });
      });
    });
  }

  function requestFeatures() {
    overwolf.games.events.setRequiredFeatures(REQUIRED_FEATURES, function (result) {
      log("Requested features", result);
    });
  }

  function registerListeners() {
    overwolf.games.events.onInfoUpdates2.addListener(function (event) {
      log("Info update", event);
      applyInfoUpdates(event.info && event.info.update ? event.info.update : []);
    });

    overwolf.games.events.onNewEvents.addListener(function (event) {
      log("New events", event);

      if (!event || !Array.isArray(event.events)) {
        return;
      }

      event.events.forEach(function (item) {
        handleGameEvent(item.name, item.data);
      });
    });

    overwolf.games.onGameInfoUpdated.addListener(function (event) {
      log("Game info updated", event);
      if (event && event.gameInfo && event.gameInfo.isRunning) {
        withOverlayWindow(function (windowId) {
          overwolf.windows.restore(windowId);
        });
      }
    });
  }

  function init() {
    restoreDeclaredWindow("desktop");
    registerHotkey();
    registerListeners();
    requestFeatures();
    emitSnapshot();
  }

  if (window.overwolf) {
    init();
  } else {
    console.warn("Overwolf runtime not detected.");
  }
})();
