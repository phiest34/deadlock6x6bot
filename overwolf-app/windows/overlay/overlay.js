(function () {
  "use strict";

  var elements = {
    hero: document.getElementById("player-hero"),
    phase: document.getElementById("phase"),
    timer: document.getElementById("timer"),
    kda: document.getElementById("kda"),
    souls: document.getElementById("souls"),
    teamScore: document.getElementById("team-score"),
    status: document.getElementById("status")
  };

  var currentSnapshot = null;

  function formatTime(seconds) {
    if (typeof seconds !== "number" || seconds < 0) {
      return "00:00";
    }

    var minutes = Math.floor(seconds / 60);
    var remainder = seconds % 60;

    return String(minutes).padStart(2, "0") + ":" + String(remainder).padStart(2, "0");
  }

  function render(snapshot) {
    currentSnapshot = snapshot;
    var player = snapshot.localPlayer || {};
    var hero = player.hero_name || player.hero_id || "Waiting for match";
    var kills = player.kills || 0;
    var deaths = player.deaths || 0;
    var assists = player.assist || 0;
    var souls = player.souls || 0;

    elements.hero.textContent = String(hero);
    elements.phase.textContent = "phase: " + (snapshot.phase || "unknown");
    elements.timer.textContent = formatTime(snapshot.estimatedMatchSeconds);
    elements.kda.textContent = [kills, deaths, assists].join(" / ");
    elements.souls.textContent = String(souls);
    elements.teamScore.textContent = snapshot.teamScore ? JSON.stringify(snapshot.teamScore) : "-";
    elements.status.textContent = snapshot.matchId
      ? "Connected to match " + snapshot.matchId
      : "No live match data yet.";
  }

  window.addEventListener("message", function (event) {
    if (!event.data || event.data.type !== "deadbot.snapshot") {
      return;
    }

    render(event.data.snapshot);
  });

  window.setInterval(function () {
    if (!currentSnapshot || typeof currentSnapshot.estimatedMatchSeconds !== "number") {
      return;
    }

    currentSnapshot.estimatedMatchSeconds += 1;
    elements.timer.textContent = formatTime(currentSnapshot.estimatedMatchSeconds);
  }, 1000);
})();
