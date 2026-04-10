# Windows Overwolf Local Run

## Goal

Локально запустить `Deadbot Overwolf`-прототип на `Windows`, проверить `bridge`, загрузить app как `unpacked extension` и снять первые `Deadlock` payloads.

## Prerequisites

- `Windows`-машина
- установленный `Deadlock`
- установленный `Overwolf`
- установленный `Python 3.9+`
- доступ к репозиторию:
  - `git clone https://github.com/phiest34/deadlock6x6bot.git`

## 1. Clone Project

Открой `PowerShell` или `Windows Terminal`:

```powershell
git clone https://github.com/phiest34/deadlock6x6bot.git
cd deadlock6x6bot
```

## 2. Prepare Python

Создай виртуальное окружение и установи зависимости:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`bridge/server.py` не требует отдельных внешних библиотек, но зависимости бота лучше поставить сразу.

## 3. Start Local Bridge

В корне проекта запусти:

```powershell
python bridge/server.py
```

Ожидаемый результат:

```text
bridge listening on http://127.0.0.1:8765
```

При старте `bridge/server.py` модуль [`bridge/capture_session.py`](/Users/moldataev.n/deadbot/bridge/capture_session.py#L1) автоматически создаст новую папку capture-сессии в:

```text
docs/overwolf-testdata/raw-payloads/<timestamp>_manual-run
```

Во время запуска `Overwolf` raw payloads будут складываться туда автоматически.

Проверь health endpoint в браузере:

```text
http://127.0.0.1:8765/health
```

Ожидаемый ответ:

```json
{"status":"ok","events_received":0,"last_snapshot_at":null,...}
```

Для проверки capture-сессии отдельно можно открыть:

```text
http://127.0.0.1:8765/capture/status
```

Там вернутся `session_dir` и счетчики по каждому типу raw payload.

## 4. Install Overwolf

Скачай и установи клиент `Overwolf`:

- [Overwolf Client](https://www.overwolf.com/download/)

После установки войди в свой `Overwolf`-аккаунт. По официальной документации для загрузки `unpacked extension` нужно быть залогиненным; иначе можно получить `Unauthorized App`.

## 5. Enable Developer Access

По документации `Overwolf` локальная загрузка делается через `Development options`.

Открой:

1. `Overwolf tray icon`
2. `Settings`
3. `About`
4. `Development options`

Если `Development options` недоступны, проверь, что аккаунт имеет developer access.

## 6. Load App As Unpacked Extension

В окне `Development options`:

1. Нажми `Load unpacked extension`
2. Выбери папку:

```text
<path-to-project>\overwolf-app
```

Важно: выбирать нужно именно корень app, где лежит `manifest.json`.

После этого приложение должно появиться в `Overwolf dock`.

## 7. Launch Desktop Window

Нажми на иконку приложения в `Overwolf dock`.

Что должно произойти:

- откроется desktop-окно приложения
- окно попробует обратиться к `http://127.0.0.1:8765/health`
- если bridge уже запущен, в desktop-окне появится сообщение, что `Bridge is healthy`

Если bridge не поднят, увидишь сообщение, что bridge offline.

## 8. Open DevTools

Чтобы дебажить окно приложения, по документации `Overwolf` можно:

1. выделить нужное окно
2. нажать `Ctrl + Shift + I`

Или открыть:

1. `Settings`
2. `About`
3. `Development options`
4. найти app и нужное окно в списке
5. открыть devtools для конкретного окна

Для первого теста важнее всего devtools у:

- `background`
- `overlay`

## 9. Run Deadlock

Запусти `Deadlock` и зайди в реальный матч.

Что мы ожидаем:

- `Overwolf` подцепит игру
- `background`-окно запросит `game_info` и `match_info`
- overlay-окно начнет получать snapshot

## 10. What To Check First

В `background` devtools проверь:

- результат `setRequiredFeatures(...)`
- результат `getRunningGameInfo(...)`
- события из `onInfoUpdates2`
- события из `onNewEvents`

Нас интересуют реальные поля:

- `phase`
- `steam_id`
- `match_id`
- `team_score`
- `roster`
- `items`
- `kills`
- `deaths`
- `assist`
- `souls`
- `hero_name` или `hero_id`

## 11. Saved Capture Files

После прогона открой созданную bridge-сессию в:

```text
docs/overwolf-testdata/raw-payloads/<timestamp>_manual-run
```

Там будут лежать:

- `set-required-features.json`
- `running-game-info.json`
- `info-updates.json`
- `new-events.json`
- `notes.md`

Если хочешь быстро проверить, что записи действительно шли в нужную сессию, сравни содержимое папки с ответом `GET /capture/status`.

Заполни `notes.md` и дальше можно разбирать payloads уже из этих файлов.

## 12. Known Caveats

- `game_id` для `Deadlock` в текущем `manifest.json` нужно подтвердить живым запуском
- прямого поля с точным `match timer` может не быть
- `net worth` может отсутствовать как готовое поле
- часть полей может приходить не сразу, а после начала матча

## 13. If App Does Not Load

Проверь по порядку:

1. запущен ли `Overwolf`
2. залогинен ли аккаунт в `Overwolf`
3. выбрана ли папка `overwolf-app`, а не корень репозитория
4. валиден ли `manifest.json`
5. доступен ли `bridge` на `127.0.0.1:8765`

## Sources

- [Basic sample app](https://dev.overwolf.com/ow-native/getting-started/onboarding-resources/basic-sample-app/)
- [Enabling and using developer tools](https://dev.overwolf.com/ow-native/guides/dev-tools/use-enable-developer-tools)
- [Testing your App](https://dev.overwolf.com/ow-native/guides/test-your-app/how-to-test-your-app)
