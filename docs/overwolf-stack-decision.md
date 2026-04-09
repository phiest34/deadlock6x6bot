# Overwolf Stack Decision

## Decision

Первый рабочий прототип делаем на `Overwolf Native App`, а не на `ow-electron`.

## Why Native First

- нам нужен быстрый `Deadlock MVP`, а не тяжелый desktop shell
- `Overwolf Native` лучше подходит для простого overlay на `HTML/CSS/JS`
- меньше operational overhead на старте
- в текущем workspace нет `node/npm`, поэтому native-каркас проще держать минимальным
- для `Deadlock` нам в первую очередь важны `GEP` и overlay windows, а не `Electron` runtime

## Why Not Electron Right Now

- `ow-electron` имеет более тяжелый стартовый footprint
- в `ow-electron` доступность game support и production rollout для `GEP` может зависеть от состояния поддержки конкретной игры
- для текущего этапа нам не нужен `Electron`-уровень интеграций

## When To Reconsider Electron

Переход на `ow-electron` можно рассмотреть позже, если появится хотя бы одно из условий:

- понадобится более сложный desktop UX
- понадобится richer local app shell с большим количеством web tooling
- native-ограничения будут мешать продуктовым требованиям
- появится подтвержденный смысл держать единую desktop-архитектуру поверх `Electron`

## Current Rule

До завершения `Phase 0` и `Phase 1` новый код для overlay пишем под `Overwolf Native`.
