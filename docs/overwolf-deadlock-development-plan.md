# Overwolf Deadlock Overlay Development Plan

## Goal

Сделать `Windows` overlay-приложение для `Deadlock` на базе `Overwolf`, которое:

- получает live-данные матча через `Overwolf GEP`
- показывает игроку ключевую информацию поверх игры
- умеет передавать события и сводку в наш существующий `Python`-бот

## Product Scope

### MVP

- определять, что пользователь находится в матче `Deadlock`
- показывать компактный overlay с:
  - текущей фазой матча
  - примерной минутой матча
  - героем игрока
  - `kills / deaths / assists`
  - `souls`
  - `team score`
- получать `steam_id` локального игрока
- отправлять live-события и snapshot в локальный bridge-сервис
- передавать данные из bridge-сервиса в текущий backend бота

### Post-MVP

- roster обеих команд
- список предметов
- post-match summary
- дополнительные экраны overlay
- настройка состава виджетов
- отправка сообщений в `Telegram` по live-событиям

## Assumptions

- `Overwolf` поддерживает `Deadlock` и отдает `game_info`, `match_info` и базовые live events.
- Точного встроенного поля с минутой матча может не быть, поэтому для `MVP` минуту считаем от `match_start` или перехода в `GameInProgress`.
- Прямого поля `net worth` может не быть; для `MVP` основной экономической метрикой считаем `souls`.
- Первый релиз делаем только под `Windows`.

## Target Architecture

### Client Side

- `Overwolf app`
- `background controller` как центральный orchestrator
- `in-game overlay window` для компактного UI
- `desktop/settings window` для авторизации, настроек и диагностики

### Data Flow

1. `Overwolf GEP` отдает события и info updates по `Deadlock`.
2. `background controller` нормализует данные в наш внутренний формат.
3. `background controller` отправляет данные в локальный `bridge` на `localhost`.
4. `Python bridge` валидирует данные и пересылает их в существующий бот или в будущий backend API.
5. Бот использует эти данные для live-уведомлений, статуса игрока и истории матчей.

### Integration Boundary

Overwolf-приложение не должно знать детали `Telegram`-бота.

Оно должно уметь только:

- собирать игровые данные
- нормализовать их
- отправлять их в локальный HTTP/WebSocket endpoint

## Recommended Tech Stack

### Overwolf App

- `Overwolf Native App`
- `TypeScript`
- `HTML/CSS`
- легкий UI без тяжелого фреймворка на первом этапе

### Local Bridge

- отдельный `Python`-процесс
- `FastAPI` или легкий `aiohttp`-сервер
- `localhost` API для приема live events от `Overwolf`

### Existing Bot Integration

- переиспользовать текущие модули, связанные с `SteamID`, профилями и хранением статуса
- добавить отдельный ingestion path для live-событий из `Overwolf`

## Current Status

- базовый каркас `Overwolf Native` app уже создан в `overwolf-app/`
- локальный `Python bridge` уже создан в `bridge/server.py`
- базовый путь `Overwolf -> localhost bridge -> bot` подготовлен
- инструкция локального запуска на `Windows` записана в `docs/windows-overwolf-local-run.md`

## External Dependency

На текущем этапе есть внешний блокер:

- заявка на `Overwolf developer access / developer whitelist` уже отправлена для аккаунта `@nur-14`
- ожидаемое время ожидания ответа: до `2` дней
- до одобрения аккаунта нельзя надежно пройти `Phase 0`, потому что `Overwolf` не дает загрузить `unpacked extension` и показывает `Unauthorized App / unauthorized source`

## Active Blocker

`Phase 0` частично заблокирован до получения `developer access` от `Overwolf`.

Что можно делать параллельно, пока идет ожидание:

- дорабатывать `bridge`
- готовить bot ingestion
- улучшать UI overlay
- фиксировать manifest/runtime issues, не требующие запуска в `Overwolf`

## Development Phases

## Phase 0. Research Spike

### Objective

Подтвердить, какие именно поля реально приходят в `Deadlock` через `Overwolf` на живом клиенте.

### Tasks

- создать минимальное `Overwolf` test app
- дождаться `Overwolf developer whitelist` для аккаунта `@nur-14`
- подписаться на:
  - `game_info`
  - `match_info`
  - live events
- логировать все raw payloads в dev console и в локальный файл
- проверить на реальном матче:
  - `steam_id`
  - `hero_name` или `hero_id`
  - `souls`
  - `kills / deaths / assist`
  - `team_score`
  - `items`
  - `roster`
  - `match_start`
  - `match_end`

### Exit Criteria

- есть подтвержденный пример реальных payloads
- понятен стабильный набор полей для `MVP`
- зафиксированы missing fields и ограничения

## Phase 1. Data Contract

### Objective

Определить внутренний формат обмена между `Overwolf app` и `Python bridge`.

### Tasks

- описать события:
  - `match.started`
  - `match.updated`
  - `player.updated`
  - `player.kda`
  - `player.souls`
  - `match.ended`
- описать общий envelope:
  - `event_type`
  - `occurred_at`
  - `source`
  - `steam_id`
  - `match_id`
  - `payload`
- определить формат heartbeat и retry
- определить deduplication keys

### Exit Criteria

- есть стабильный JSON contract
- bridge и overlay используют один и тот же schema layer

## Phase 2. Local Bridge

### Objective

Поднять локальный сервис для приема данных от overlay.

### Tasks

- создать `Python` bridge-сервис
- поднять `localhost` endpoint для:
  - `POST /events`
  - `POST /snapshot`
  - `GET /health`
- добавить:
  - валидацию payload
  - логирование
  - простую буферизацию
  - deduplication
- хранить последние события по активному матчу

### Exit Criteria

- overlay может отправлять события локально
- сервис переживает перезапуск окна overlay
- последние события доступны для отладки

## Phase 3. MVP Overlay UI

### Objective

Сделать полезный и компактный in-game overlay.

### Tasks

- окно overlay с always-on-top поведением внутри `Overwolf`
- компактный блок с:
  - герой
  - `K/D/A`
  - `souls`
  - `team score`
  - таймер матча
- состояние `not in match`
- состояние `data unavailable`
- hotkey для показа/скрытия
- базовые настройки размера и позиции

### Exit Criteria

- overlay стабильно отображается в матче
- данные обновляются без ручного refresh
- UI остается читаемым в реальной игре

## Phase 4. Bot Integration

### Objective

Связать новые live-данные с текущим ботом.

### Tasks

- добавить ingestion handler в существующий backend
- сопоставлять `Overwolf steam_id` с игроками в базе
- обновлять активный статус матча точнее, чем через `Steam Web API`
- использовать live feed для:
  - более точной минуты матча
  - live-статуса игрока
  - пост-матч сводки
- добавить fallback на старый `Steam Web API`, если overlay недоступен

### Exit Criteria

- бот принимает и использует live-данные
- при наличии overlay данные приоритетнее старого polling-механизма

## Phase 5. Reliability

### Objective

Сделать систему устойчивой к рестартам и пропускам событий.

### Tasks

- retry на отправку событий в bridge
- локальный event queue
- обработка смены матча и внезапного закрытия игры
- защита от дублирования `match_start` и `match_end`
- health diagnostics экран
- versioning для event schema

### Exit Criteria

- система не теряет основной матчевый контекст при кратковременных сбоях
- ошибки можно диагностировать без дебага в коде

## Phase 6. Distribution

### Objective

Подготовить приложение к использованию вне dev-среды.

### Tasks

- dev/prod конфиги
- инструкции по локальному запуску
- упаковка bridge-процесса
- автозапуск bridge при старте приложения или явная установка
- проверка ограничений `Overwolf` на публикацию и game support policy

### Exit Criteria

- можно установить приложение на чистую `Windows`-машину
- запуск и связка с ботом воспроизводимы по инструкции

## Milestones

### Milestone 1

`Deadlock` raw events успешно читаются через `Overwolf`.

### Milestone 2

Overlay показывает игроку live `K/D/A`, `souls`, героя и таймер.

### Milestone 3

Локальный bridge принимает события и пишет их в лог/хранилище.

### Milestone 4

Бот использует данные overlay вместо приблизительного определения матча.

## Risks

### Technical Risks

- часть полей в `Overwolf GEP` может быть нестабильной после патчей `Deadlock`
- `net worth` может отсутствовать как готовое поле
- `steam_id` и локальный игрок могут определяться не во всех состояниях матча
- `roster/items` могут приходить с задержкой или неполно

### Product Risks

- полезность overlay окажется ниже ожиданий, если live data ограничены
- зависимость от `Overwolf` накладывает требования на дистрибуцию и UX

## Risk Mitigation

- строить `MVP` вокруг подтвержденных полей, а не желаемых
- считать таймер из событий, если нет явного `match clock`
- использовать `souls` как основную экономическую метрику до появления надежного `net worth`
- сохранять fallback на текущий `Steam Web API` polling

## Initial Backlog

- создать папку `overwolf-app/`
- поднять минимальный `manifest.json`
- сделать `background` окно
- подключить `overwolf.games.events`
- вывести raw `Deadlock` payload в лог
- зафиксировать реальные payload examples в отдельном документе
- создать `bridge/` на `Python`
- описать JSON schema для событий
- сделать первый overlay screen
- связать `steam_id` из overlay с текущей базой бота

## Definition of Success

Проект считается успешным, если:

- пользователь запускает `Deadlock`
- overlay автоматически появляется в матче
- игрок видит live-статы без ручного ввода
- локальный bridge получает данные в реальном времени
- бот умеет использовать эти данные для live-логики и уведомлений

## Next Step

Следующий практический шаг: реализовать `Phase 0` и получить реальные `Deadlock` payloads из `Overwolf`, прежде чем писать production UI и интеграцию с ботом.
