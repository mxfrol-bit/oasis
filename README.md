# OASIS Bot + Mini App

Один Python-процесс на Railway. Внутри:
- **aiogram polling** — обработка команд бота (`/start`, `/grant`, `/find`)
- **aiohttp HTTP server** — `/api/auth` для Mini App + раздача статики `/` и `/assets/*`

Mini App грузится с того же домена что и `/api/auth`. После авторизации ходит **напрямую в Supabase REST** с JWT (никакого прокси-уровня) — это снимает нагрузку с бота и работает реалтайм-быстро.

## Архитектура одной картинкой

```
┌──────────────────────────────────────────────────────────────┐
│  Telegram client                                              │
│                                                               │
│  /start ─┐                          ┌── open WebApp           │
│          ▼                          ▼                         │
│  ┌────────────────────────────────────────────────┐          │
│  │  Railway: oasis-bot (Python, port 8080)        │          │
│  │  ├─ aiogram polling                            │          │
│  │  └─ aiohttp:                                   │          │
│  │     ├─ GET  /            → web/index.html      │          │
│  │     ├─ GET  /assets/*    → web/assets/*        │          │
│  │     ├─ POST /api/auth    → validate initData,  │          │
│  │     │                      register_user,      │          │
│  │     │                      issue JWT           │          │
│  │     └─ GET  /health                            │          │
│  └────────────────────────────────────────────────┘          │
│           │                                                   │
│           │ register_user (service_role, обход RLS)           │
│           │                                                   │
│           │  ┌─── JWT с claim tg_id ──┐                       │
│           ▼  ▼                         │                      │
│  ┌─────────────────────────────────────┴─────┐               │
│  │  Supabase Postgres                         │               │
│  │  - 9 таблиц (users, profiles, rooms…)      │               │
│  │  - 8 RPC (open_room, close_level, …)       │               │
│  │  - RLS читает tg_id из JWT                 │               │
│  └────────────────────────────────────────────┘               │
│                       ▲                                       │
│                       │ RPC напрямую с JWT                    │
│   Mini App (vanilla HTML/JS, 1 файл) ─────────────────────────┤
└──────────────────────────────────────────────────────────────┘
```

## Деплой на Railway за 5 минут

### 1. Подготовка
- Распакуй zip локально
- Зайди в папку `bot/`

### 2. Деплой
```bash
# вариант A: через CLI
railway login
railway init    # создать новый сервис в существующем проекте или новом
railway up

# вариант B: подключить GitHub-репо
# залей репо на GitHub, в Railway → New Project → Deploy from GitHub Repo
```

### 3. Variables в Railway
Settings → Variables → залить из `.env.example`:

| Variable | Откуда взять |
|---|---|
| `BOT_TOKEN` | @BotFather → /mybots → @RSroom_bot → API Token |
| `BOT_USERNAME` | `RSroom_bot` (без @) |
| `SUPABASE_URL` | `https://zrsdziwgtqqysdrmijzx.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase Settings → API → API Keys → **anon public** |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Settings → API → API Keys → **service_role** (секрет!) |
| `SUPABASE_JWT_SECRET` | Supabase Settings → API → JWT Keys → **Legacy JWT secret** |
| `PUBLIC_URL` | После первого деплоя: Settings → Networking → **Generate Domain** → копировать URL |

### 4. Подключить Mini App к боту
1. После деплоя в Railway скопировать сгенерированный `PUBLIC_URL` (вида `https://oasis-bot-production-XXXX.up.railway.app`)
2. Залить его в Variables как `PUBLIC_URL`, **перезапустить сервис**
3. @BotFather → `/mybots` → `@RSroom_bot` → **Bot Settings** → **Configure Menu Button** → **Configure menu button** → ввести URL: `https://oasis-bot-production-XXXX.up.railway.app/`

### 5. Сделать себя GM
1. Открой `@RSroom_bot` в Telegram → `/start`
2. Бот пришлёт твой `telegram_id`. Можно также через `/me`
3. Зайди в Supabase SQL Editor: `update public.users set is_gm = true where telegram_id = <твой_id>;`
4. После этого у тебя в боте работают `/grant @user 500 [причина]` и `/find @user`

## Команды бота

| Команда | Кому | Что |
|---|---|---|
| `/start` | всем | Регистрация / возврат, парсит реф-код из `?start=ref_XXXXXXX` |
| `/me` | всем | tg_id, баланс, реф-код, статус GM |
| `/help` | всем | Описание игры |
| `/find @user` | GM | Карточка юзера |
| `/grant @user 500 [причина]` | GM | Начислить/списать KEY (отрицательное число — списать) |

## Структура

```
bot/
├── main.py                — entry: aiohttp + aiogram parallel
├── server.py              — aiohttp routes (auth, static, health)
├── handlers/
│   ├── start.py           — /start, реф-парсинг
│   ├── gm.py              — /grant, /find, /me
│   └── common.py          — /help
├── services/
│   ├── supabase_client.py — REST + HS256 JWT generation
│   └── webapp_auth.py     — Telegram WebApp HMAC validation
├── web/
│   ├── index.html         — Mini App (vanilla, 636 строк)
│   └── assets/            — 24 jpg сцены + лого
├── requirements.txt
├── Procfile               — web: python main.py
└── .env.example
```

## Тестирование локально

Mini App через `window.Telegram.WebApp` валиден только в Telegram. Для локальной разработки можно использовать [ngrok](https://ngrok.com/) чтобы пробросить локальный порт в HTTPS, затем подставить в BotFather как Menu Button URL.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # заполни
export $(cat .env | xargs)
python main.py
# в другом терминале
ngrok http 8080
# полученный https URL → @BotFather → Menu Button
```

## Что внутри MVP

- ✅ Регистрация через `/start` или прямой вход в Mini App (с реф-кодом или без)
- ✅ Welcome bonus 500 KEY
- ✅ 12 уровней с прогрессией (Хостел I → Оазис)
- ✅ Открытие комнаты за KEY, 5 слотов, заполнение через рефералы
- ✅ Авто-разлив pending-рефералов при открытии новой комнаты
- ✅ Закрытие уровня с наградой KEY
- ✅ Реф-ссылка с кнопкой "Поделиться" (нативный Telegram share)
- ✅ Кабинет: баланс, история транзакций, "Перевод в игру" (mock pending)
- ✅ Путь: 12 ступеней с визуальным статусом
- ✅ GM-команды: `/grant`, `/find`, аудит в `gm_actions`
- ⏳ Бонусы (автозаполнение, страховка, ускоритель, приоритет) — UI готов, логика во второй итерации
- ⏳ Realtime обновление слотов через Supabase Realtime — после первой проверки
- ⏳ Стили жилья и приватность профиля — после первой проверки
