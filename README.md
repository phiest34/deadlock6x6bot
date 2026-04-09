# Deadlock Telegram Bot

`Telegram`-бот на `Python`, который следит за друзьями в `Steam` и пишет, когда они заходят в `Deadlock`.

## Что умеет

- `/hero <герой>` показывает краткую справку по герою
- `/tip` выдает случайный совет
- `/addfriend <steam vanity/link/id> [псевдоним]` добавляет игрока в мониторинг
- `/importfriends <steam vanity/link/id>` добавляет всех публичных друзей профиля
- `/removefriend <steam vanity/link/id>` убирает игрока из мониторинга
- `/profile <steam vanity/link/id>` показывает краткий профиль игрока
- `/heroes <steam vanity/link/id> [alltime|recent]` показывает топ героев игрока
- `/live <steam vanity/link/id>` пытается показать live-информацию о текущем матче
- `/friends` показывает список отслеживаемых игроков
- `/check` вручную проверяет, кто сейчас в `Deadlock`, и показывает примерную минуту в игре
- `/helpme` показывает список команд

Фоновая задача опрашивает `Steam Web API` и пишет в чат только при смене статуса:

- игрок зашел в `Deadlock`
- игрок вышел из `Deadlock`

`/addfriend` принимает:

- ссылку вида `https://steamcommunity.com/profiles/...`
- vanity-ссылку вида `https://steamcommunity.com/id/...`
- просто vanity-имя профиля

Снаружи бот работает через `vanity` и ссылки профиля. Внутри он сам резолвит и хранит `SteamID64`, но пользователю его не показывает.

`/importfriends` использует `ISteamUser/GetFriendList`. По официальной документации Valve он работает только для профилей с публичным friends list.

Показатель “минута в игре” сейчас приблизительный: бот считает его с момента, когда впервые увидел игрока в `Deadlock` через `Steam Web API`, а не из точного live-таймера матча.

`/live` использует публичный endpoint `deadlock-api` `/v1/matches/active`. Он показывает только матчи, попавшие в их live watch pool, поэтому live-данные находятся не для каждого игрока.

## Запуск

1. Создай и активируй виртуальное окружение.
2. Установи зависимости:

```bash
pip install -r requirements.txt
```

3. Создай `.env` на основе `.env.example` и укажи:

- `TELEGRAM_BOT_TOKEN`
- `STEAM_API_KEY`
- при необходимости `STEAM_POLL_INTERVAL_SECONDS`
- при необходимости `DATABASE_PATH`

4. Запусти:

```bash
python bot.py
```

## Что можно улучшить дальше

- добавить привязку через vanity URL или профиль Steam
- пробовать оценивать минуту текущего матча через community API
- хранить отдельные настройки по чатам и частоте уведомлений
- добавить команды для последнего матча и ранга
