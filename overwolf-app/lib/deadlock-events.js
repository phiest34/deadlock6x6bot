(function () {
  "use strict";

  function safeJsonParse(value) {
    if (typeof value !== "string") {
      return value;
    }

    try {
      return JSON.parse(value);
    } catch (_error) {
      return value;
    }
  }

  function toMap(entries) {
    var output = {};

    if (!Array.isArray(entries)) {
      return output;
    }

    entries.forEach(function (entry) {
      if (!entry || typeof entry.name !== "string") {
        return;
      }

      output[entry.name] = safeJsonParse(entry.data);
    });

    return output;
  }

  function extractLocalPlayer(roster, steamId) {
    if (!Array.isArray(roster) || !steamId) {
      return null;
    }

    for (var index = 0; index < roster.length; index += 1) {
      var player = roster[index];
      if (!player) {
        continue;
      }

      if (String(player.steam_id) === String(steamId)) {
        return player;
      }
    }

    return null;
  }

  function buildSnapshot(state) {
    var roster = Array.isArray(state.roster) ? state.roster : [];
    var localPlayer = extractLocalPlayer(roster, state.steamId);

    return {
      phase: state.phase || "unknown",
      gameMode: state.gameMode || null,
      matchId: state.matchId || null,
      steamId: state.steamId || null,
      teamScore: state.teamScore || null,
      roster: roster,
      localPlayer: localPlayer,
      timerStartedAt: state.timerStartedAt || null,
      estimatedMatchSeconds: state.timerStartedAt
        ? Math.max(0, Math.floor((Date.now() - state.timerStartedAt) / 1000))
        : null,
      lastEvent: state.lastEvent || null,
      updatedAt: new Date().toISOString()
    };
  }

  function normalizeInfoUpdates(infoUpdates) {
    var map = toMap(infoUpdates);

    return {
      phase: map.phase || null,
      gameMode: map.game_mode || null,
      matchId: map.match_id || null,
      steamId: map.steam_id || null,
      teamScore: map.team_score || null,
      roster: map.roster || null,
      items: map.items || null,
      raw: map
    };
  }

  function normalizeGameEvent(eventName, eventData) {
    return {
      type: "deadlock.event",
      eventName: eventName,
      payload: safeJsonParse(eventData),
      occurredAt: new Date().toISOString()
    };
  }

  window.deadlockEvents = {
    buildSnapshot: buildSnapshot,
    normalizeGameEvent: normalizeGameEvent,
    normalizeInfoUpdates: normalizeInfoUpdates
  };
})();
