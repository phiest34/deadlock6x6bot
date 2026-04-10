# Capture Notes Template

Заполняй только короткий человеческий контекст, которого нет в raw json.

## Required

- Scenario:
  Короткое имя сценария. Пример: `ranked-midgame`, `bots-match-start`, `post-match`.
- Game mode:
  Какой режим был в игре. Это нужно, потому что набор payloads может зависеть от режима.
- Match stage:
  На каком этапе снят payload. Пример: `pre-match`, `start`, `midgame`, `late`, `post-match`.
- Real match or bots:
  Помогает понять, можно ли считать этот capture источником истины для MVP.
- Attach and features:
  Коротко: сработал ли attach и прошел ли `setRequiredFeatures(...)`.

## Confirmed Fields

- Confirmed fields:
  Перечисли только то, что реально подтвердилось в этой сессии. Пример: `steam_id, match_id, phase, roster, souls`.

## Oddities

- Missing or odd fields:
  Что ожидалось, но не пришло, или пришло странно. Пример: `items empty`, `team_score appeared late`.
- Errors:
  Любые ошибки runtime, bridge или подписки. Если ошибок не было, так и напиши.

## Fixture Notes

- Candidate fixtures:
  Какие маленькие сценарии стоит потом вынести в `fixtures/`.

## Minimal Example

- Scenario: `ranked-midgame`
- Game mode: `ranked`
- Match stage: `midgame`
- Real match or bots: `real match`
- Attach and features: `attach ok, setRequiredFeatures ok`
- Confirmed fields: `steam_id, match_id, phase, roster, souls, new_events`
- Missing or odd fields: `items empty, team_score appeared only after first fight`
- Errors: `none`
- Candidate fixtures: `match-start-basic`, `score-change-midgame`
