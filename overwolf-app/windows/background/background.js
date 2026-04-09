(function () {
  "use strict";

  var REQUIRED_FEATURES = ["game_info", "match_info"];
  var BRIDGE_BASE_URL = "http://127.0.0.1:8765";
  var GAME_INFO_POLL_INTERVAL_MS = 5000;
  var FEATURE_RETRY_INTERVAL_MS = 4000;
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
  window.deadbotDebugState = {
    requestedFeatures: null,
    runningGameInfo: null,
    lastGameInfoUpdate: null,
    lastInfoUpdate: null,
    lastNewEvents: null,
    lastSnapshot: null,
    lastBridgeError: null,
    lastFeatureRequestAttemptAt: null,
    updatedAt: new Date().toISOString()
  };
  var featureRetryTimerId = null;

  function log(message, data) {
    if (typeof data === "undefined") {
      console.log("[deadbot]", message);
      return;
    }

    if (typeof data === "string") {
      console.log("[deadbot]", message, data);
      return;
    }

    try {
      console.log("[deadbot]", message, JSON.stringify(data));
    } catch (_error) {
      console.log("[deadbot]", message, data);
    }
  }

  function sendToOverlay(message) {
    overwolf.windows.obtainDeclaredWindow("overlay", function (result) {
      if (!result.success || !result.window) {
        log("Overlay window is unavailable", result);
        return;
      }

      if (typeof result.window.postMessage !== "function") {
        log("Overlay window postMessage API is unavailable", result.window);
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
      window.deadbotDebugState.lastBridgeError = {
        path: path,
        message: String(error),
        updatedAt: new Date().toISOString()
      };
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
    window.deadbotDebugState.lastSnapshot = snapshot;
    window.deadbotDebugState.updatedAt = new Date().toISOString();
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
    if (
      !overwolf.settings ||
      typeof overwolf.settings.registerHotKey !== "function"
    ) {
      log("Hotkey API is unavailable in this runtime");
      return;
    }

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
    window.deadbotDebugState.lastFeatureRequestAttemptAt = new Date().toISOString();
    overwolf.games.events.setRequiredFeatures(REQUIRED_FEATURES, function (result) {
      window.deadbotDebugState.requestedFeatures = result;
      window.deadbotDebugState.updatedAt = new Date().toISOString();
      log("Requested features", result);
    });
  }

  function ensureFeatureRetryLoop() {
    if (featureRetryTimerId !== null) {
      return;
    }

    featureRetryTimerId = window.setInterval(function () {
      requestFeatures();
    }, FEATURE_RETRY_INTERVAL_MS);
  }

  function stopFeatureRetryLoop() {
    if (featureRetryTimerId === null) {
      return;
    }

    window.clearInterval(featureRetryTimerId);
    featureRetryTimerId = null;
  }

  function pollRunningGameInfo() {
    if (!overwolf.games || typeof overwolf.games.getRunningGameInfo !== "function") {
      log("getRunningGameInfo API is unavailable in this runtime");
      return;
    }

    overwolf.games.getRunningGameInfo(function (result) {
      window.deadbotDebugState.runningGameInfo = result;
      window.deadbotDebugState.updatedAt = new Date().toISOString();
      log("Running game info", result);
    });
  }

  function registerListeners() {
    overwolf.games.events.onInfoUpdates2.addListener(function (event) {
      window.deadbotDebugState.lastInfoUpdate = event;
      window.deadbotDebugState.updatedAt = new Date().toISOString();
      log("Info update", event);
      stopFeatureRetryLoop();
      applyInfoUpdates(event.info && event.info.update ? event.info.update : []);
    });

    overwolf.games.events.onNewEvents.addListener(function (event) {
      window.deadbotDebugState.lastNewEvents = event;
      window.deadbotDebugState.updatedAt = new Date().toISOString();
      log("New events", event);

      if (!event || !Array.isArray(event.events)) {
        return;
      }

      event.events.forEach(function (item) {
        handleGameEvent(item.name, item.data);
      });
    });

    overwolf.games.onGameInfoUpdated.addListener(function (event) {
      window.deadbotDebugState.lastGameInfoUpdate = event;
      window.deadbotDebugState.updatedAt = new Date().toISOString();
      log("Game info updated", event);
      if (event && event.gameInfo && event.gameInfo.isRunning) {
        requestFeatures();
        ensureFeatureRetryLoop();
      }
    });
  }

  function init() {
    restoreDeclaredWindow("desktop");
    registerHotkey();
    registerListeners();
    pollRunningGameInfo();
    window.setInterval(pollRunningGameInfo, GAME_INFO_POLL_INTERVAL_MS);
    requestFeatures();
    emitSnapshot();
  }

  if (window.overwolf) {
    init();
  } else {
    console.warn("Overwolf runtime not detected.");
  }
})();
