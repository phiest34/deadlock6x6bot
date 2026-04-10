# Overwolf Testing Pipeline

## Goal

Сократить цикл разработки `Overwolf`-приложения так, чтобы большинство изменений можно было проверять без полного ручного прогона `Overwolf + Deadlock + Windows match`.

## Problems With Current Flow

Текущий процесс из [windows-overwolf-local-run.md](/Users/moldataev.n/deadbot/docs/windows-overwolf-local-run.md) подходит для первого живого запуска, но неудобен для повседневной разработки:

- слишком долгий feedback loop
- баги в нормализации payloads трудно воспроизводить
- мелкие правки требуют повторного захода в матч
- нельзя быстро проверить `bridge` и schema-слой независимо от `Overwolf runtime`

## Target Pipeline

Разработка и тестирование должны идти в четыре слоя.

### 1. Payload Capture

Источник истины для проекта.

Что делаем:

- на `Windows` запускаем реальный `Overwolf` и реальный матч `Deadlock`
- поднимаем локальный bridge через `python bridge/server.py`
- `bridge/server.py` принимает HTTP payloads, а `bridge/capture_session.py` сохраняет их в файловую capture-сессию
- сохраняем raw output:
  - `setRequiredFeatures(...)`
  - `getRunningGameInfo(...)`
  - `onInfoUpdates2`
  - `onNewEvents`
- фиксируем контекст capture:
  - дата
  - игровой режим
  - стадия матча
  - версия app
  - заметки по странностям payloads

Результат:

- у нас есть реальные payloads, на которых строится весь остальной pipeline

### 2. Fixture Replay

Основной быстрый цикл разработки.

Что делаем:

- из raw payloads формируем fixtures
- локально прогоняем fixtures через слой нормализации
- проверяем normalized events и snapshots без запуска `Overwolf`

Результат:

- изменения в `overwolf-app/lib/deadlock-events.js` можно проверять быстро и воспроизводимо

### 3. Bridge Contract Tests

Проверка локального ingestion-layer отдельно от `Overwolf runtime`.

Что делаем:

- подаем fixtures в HTTP-контракт `bridge/server.py`
- проверяем:
  - прием валидных payloads
  - отбрасывание невалидных payloads
  - обновление snapshot
  - запись capture payloads в файловую сессию
  - debug endpoints: `/health` и `/capture/status`

Результат:

- `bridge` тестируется как обычный backend-компонент

### 4. Simulated App Smoke

Быстрый ручной smoke без реального `Overwolf`.

Что делаем:

- подменяем runtime на fake implementation
- воспроизводим сценарии:
  - attach к игре
  - `Info Update`
  - `New Events`
  - `bridge offline`
  - `match_end`

Результат:

- можно быстро проверять `background` и `desktop debug panel` без входа в матч

### 5. Real Windows Smoke

Редкий дорогой прогон.

Когда запускать:

- после появления новых live payloads
- после патчей `Deadlock` или `Overwolf`
- перед крупным merge
- после изменений в game targeting или feature subscription

Что проверяем:

- attach к игре
- feature subscription
- соответствие реальных payloads текущему контракту
- отсутствие регрессий в debug flow

## Recommended Development Loop

Для обычной разработки используем такой порядок:

1. Один раз снять raw payloads на `Windows`.
2. Сохранить их в репозитории.
3. Прогонять replay и contract tests локально много раз.
4. Периодически запускать simulated smoke.
5. Реальный `Windows` smoke делать только на checkpoint-этапах.

## Repository Layout

Все артефакты тестирования `Overwolf` храним в одном месте:

- [overwolf-testdata/README.md](/Users/moldataev.n/deadbot/docs/overwolf-testdata/README.md)
- [capture-log-template.md](/Users/moldataev.n/deadbot/docs/overwolf-testdata/capture-log-template.md)
- [raw-payloads/](/Users/moldataev.n/deadbot/docs/overwolf-testdata/raw-payloads)
- [fixtures/](/Users/moldataev.n/deadbot/docs/overwolf-testdata/fixtures)

Назначение каталогов:

- `raw-payloads/`
  хранит сырые payloads из реальных прогонов
- `fixtures/`
  хранит стабильные тестовые сценарии для replay и automated tests

Внутри `raw-payloads/` и `fixtures/` отдельные README не нужны: этот документ и `overwolf-testdata/README.md` покрывают правила хранения.

## How To Store New Payloads

После каждого живого прогона на `Windows`:

1. Запустить `python bridge/server.py`.
2. При старте `bridge/capture_session.py` автоматически создаст новую capture-сессию внутри `raw-payloads/`.
3. Во время ручного прогона `Overwolf` raw payloads будут автоматически записываться в:
   - `set-required-features.json`
   - `running-game-info.json`
   - `info-updates.json`
   - `new-events.json`
4. Для быстрой проверки можно открыть `http://127.0.0.1:8765/capture/status` и убедиться, что счетчики растут.
5. После завершения прогона открыть созданную папку и заполнить `notes.md` по шаблону.
6. Если payload подходит для регрессионного теста, на его основе сделать fixture в `fixtures/`.

## Fixture Rules

Каждый fixture должен быть маленьким и целевым.

Хорошие fixtures:

- `match-start-basic.json`
- `score-update.json`
- `local-player-kda-update.json`
- `match-end-basic.json`
- `bridge-offline-no-crash.json`

Плохие fixtures:

- один огромный json с целым матчем без структуры
- fixture, который одновременно покрывает десятки кейсов

Для каждого fixture нужно хранить:

- краткое имя сценария
- источник raw payload
- ожидаемый результат нормализации
- важные поля, которые fixture проверяет

## Minimal Next Steps

Чтобы этот pipeline стал рабочим, следующие инженерные шаги такие:

1. Снять первый комплект raw payloads и разложить его в `raw-payloads/`.
2. Утвердить минимальный JSON contract для normalized events.
3. Добавить replay-скрипт для `deadlock-events.js`.
4. Добавить тесты для `bridge/server.py` и `bridge/capture_session.py` на этих fixtures.
5. Добавить runtime adapter или fake runtime для quick smoke.

## Exit Criteria

Pipeline считается внедренным, когда:

- реальные payloads лежат в репозитории в стандартизированном виде
- fixtures можно переиспользовать для локальной проверки
- `bridge` можно тестировать без запуска игры
- для живого `Windows` smoke есть понятный чеклист и структура артефактов
