# Overwolf Test Data

Краткий индекс для тестовых данных `Overwolf`.

Основной документ с пайплайном и правилами:

- [overwolf-testing-pipeline.md](/Users/moldataev.n/deadbot/docs/overwolf-testing-pipeline.md)

Что лежит здесь:

- [raw-payloads/](/Users/moldataev.n/deadbot/docs/overwolf-testdata/raw-payloads)
  сырые данные из реального `Overwolf runtime`
- [fixtures/](/Users/moldataev.n/deadbot/docs/overwolf-testdata/fixtures)
  компактные сценарии для replay и тестов
- [capture-log-template.md](/Users/moldataev.n/deadbot/docs/overwolf-testdata/capture-log-template.md)
  короткий шаблон для `notes.md`

## Quick Workflow

1. Запусти `python bridge/server.py`.
2. `bridge/capture_session.py` автоматически создаст новую папку capture-сессии в `raw-payloads/`.
3. Запусти `Overwolf` app и зайди в нужный игровой сценарий.
4. Raw payloads автоматически сохранятся в json-файлы этой сессии.
5. При необходимости проверь `http://127.0.0.1:8765/capture/status`, чтобы увидеть путь к сессии и текущие счетчики.
6. После прогона открой `notes.md` и заполни контекст capture.
7. Отметь, какие payloads годятся для регрессионных тестов.
8. Вынеси из них маленькие fixtures в `fixtures/`.
