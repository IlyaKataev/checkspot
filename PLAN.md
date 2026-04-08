# CheckSpot MVP — Подробный план реализации

## Что есть сейчас

В `retail_audit_app/` — фронтенд-прототип (React + Vite + Tailwind + shadcn/ui):
- `ChatBot.tsx` — симуляция Telegram-бота в браузере (без реального бота)
- `ClientDashboard.tsx` — ЛК заказчика с кампаниями и отчётами
- `ClientLogin.tsx` — форма входа

Всё замоканo, нет бэкенда, нет реального Telegram-бота. Прототип трогать не будем — будем делать отдельно.

---

## Архитектура MVP

```
checkspot/
├── backend/              # Python + FastAPI
│   ├── app/
│   │   ├── api/          # REST эндпоинты (для дашборда)
│   │   ├── bot/          # Telegram bot (aiogram 3)
│   │   ├── core/         # конфиг, JWT, база
│   │   ├── models/       # SQLAlchemy ORM
│   │   ├── schemas/      # Pydantic (входные/выходные данные)
│   │   └── services/     # бизнес-логика
│   ├── alembic/          # миграции БД
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/             # React + Vite (адаптируем из прототипа)
│   ├── src/
│   │   ├── api/          # HTTP-клиент к бэкенду
│   │   ├── components/   # компоненты (берём из retail_audit_app)
│   │   ├── pages/        # страницы
│   │   └── store/        # состояние (zustand)
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

**Стек:**
| Компонент | Технология |
|-----------|-----------|
| Backend API | Python 3.12 + FastAPI + uvicorn |
| Telegram Bot | aiogram 3.x (async) |
| База данных | PostgreSQL 16 |
| ORM + миграции | SQLAlchemy 2 + Alembic |
| Авторизация | JWT (dashboard) + Telegram user_id (bot) |
| Хранилище фото | локальная папка `/media` (MVP), S3 потом |
| AI-проверка фото | Claude API (claude-haiku — быстро и дёшево) |
| Frontend | React 18 + Vite + Tailwind + shadcn/ui |
| HTTP-клиент | axios + react-query |
| Запуск | Docker Compose |

---

## База данных

### Таблицы

```sql
-- Пользователи (все роли)
users
  id, telegram_id (nullable), email (nullable), phone, role (executor/client),
  name, is_active, created_at, agreed_at

-- Клиенты (B2B) — расширение users
clients
  id, user_id FK, company_name, balance, plan (basic/pro)

-- Исполнители — расширение users
executors
  id, user_id FK, balance, completed_tasks, rating, lat, lng, last_seen_at

-- Кампании (создаёт заказчик)
campaigns
  id, client_id FK, name, category, description, price_per_task, status (draft/active/completed),
  created_at, published_at, deadline

-- Задания (точки проверки) — создаются из кампании
tasks
  id, campaign_id FK, address, lat, lng, status (available/in_progress/completed/rejected),
  executor_id FK nullable, accepted_at, deadline_at, completed_at

-- Отчёты по заданиям (результат выполнения)
task_reports
  id, task_id FK, executor_id FK, photo_path, photo_taken_at, photo_lat, photo_lng,
  ai_check_result (json), ai_passed, client_confirmed, created_at, rejection_reason

-- Выплаты исполнителям
payouts
  id, executor_id FK, amount, status (pending/completed/failed), method, created_at, completed_at

-- Уведомления
notifications
  id, user_id FK, type, title, body, is_read, created_at, meta (json)

-- Обращения в поддержку / жалобы
support_tickets
  id, user_id FK, task_id FK nullable, type (support/complaint), message, status, created_at
```

---

## Фазы реализации

### Фаза 1: Бэкенд — основа (3-4 дня)

**1.1 Структура проекта**
- [ ] Инициализация FastAPI приложения
- [ ] Конфиг через pydantic-settings (`.env`)
- [ ] Подключение PostgreSQL (asyncpg + SQLAlchemy async)
- [ ] Alembic: первая миграция (все таблицы)
- [ ] CORS настройки

**1.2 Авторизация**
- [ ] JWT: создание, валидация токенов
- [ ] Endpoint POST `/api/auth/login` (email + password)
- [ ] Endpoint POST `/api/auth/register` (клиент)
- [ ] Telegram auth middleware (проверка user_id + подпись)
- [ ] Зависимость `get_current_client` / `get_current_executor`

**1.3 Файловое хранилище**
- [ ] Endpoint POST `/api/media/upload` (multipart)
- [ ] Сохранение в `/media/photos/` с UUID именем
- [ ] Endpoint GET `/media/{filename}` (статика)

**1.4 Базовые CRUD эндпоинты**
```
POST /api/campaigns                    — создать кампанию
GET  /api/campaigns                    — список кампаний клиента
GET  /api/campaigns/{id}               — детали кампании
POST /api/campaigns/{id}/publish       — опубликовать кампанию
GET  /api/campaigns/{id}/tasks         — задания кампании
GET  /api/campaigns/{id}/reports       — отчёты по кампании
GET  /api/campaigns/{id}/export        — экспорт в CSV

GET  /api/tasks?lat=&lng=&radius=      — задания рядом (для бота)
POST /api/tasks/{id}/accept            — взять задание
POST /api/tasks/{id}/submit            — отправить фото + результат
POST /api/tasks/{id}/confirm           — подтвердить клиентом

GET  /api/executor/balance             — баланс исполнителя
POST /api/executor/payout              — запрос на выплату
GET  /api/executor/tasks               — история заданий

GET  /api/notifications                — уведомления пользователя
POST /api/support/ticket               — обращение в поддержку
```

---

### Фаза 2: AI-проверка фото (1-2 дня)

**Логика проверки (Claude claude-haiku-4-5):**

При загрузке фото от исполнителя запускается асинхронная задача:

1. **GPS-валидация**: сравниваем координаты фото (из EXIF или переданные ботом) с координатами задания. Допуск: 100 метров.

2. **AI-проверка через Claude**:
   - Промпт: `"Is this a photo of a retail shelf? Does it clearly show [category]? Is the image clear and not blurry? Answer in JSON: {is_shelf: bool, is_clear: bool, has_category: bool, reason: string}"`
   - Модель: `claude-haiku-4-5-20251001` (быстро, дёшево)

3. **Результат**:
   - Всё OK → статус задания `completed`, начисляем оплату исполнителю
   - Провалено → статус `rejected`, уведомление с причиной

**Сервис `services/ai_checker.py`:**
```python
async def check_photo(photo_path: str, category: str) -> AICheckResult:
    # base64 фото → Claude API → parse JSON ответ
```

---

### Фаза 3: Telegram-бот (3-4 дня)

**Бот на aiogram 3, webhook через FastAPI.**

#### 3.1 Онбординг исполнителя

```
/start
  → Приветствие + кнопка "Начать"
  → Запрос номера телефона (кнопка "Поделиться" или ввод)
  → Показ соглашения + кнопки "Согласен/Не согласен"
  → Если согласен → регистрация в БД → главное меню
```

**Главное меню:**
```
🔍 Найти задания
💰 Мой баланс
📋 История
❓ Поддержка
```

#### 3.2 Поиск и выполнение задания

```
"Найти задания"
  → Запрос геолокации (кнопка Telegram location)
  → GET /api/tasks?lat=&lng=&radius=2000
  → Показ карточек (адрес, категория, оплата, расстояние, время)
  → Кнопка "Взять задание"
  → POST /api/tasks/{id}/accept
  → Инструкция + таймер 30 мин
  → Кнопка "Отправить фото"
  → Получаем фото от пользователя
  → "Проверяю..." (анимация)
  → AI check → результат
  → Если OK: "✅ +150₽ начислены!"
  → Если нет: причина + "Попробовать снова"
```

#### 3.3 Уведомления (push из бэкенда)
- При появлении нового задания рядом: "📍 Новое задание рядом: ул. Ленина, 10. 150₽"
- При проверке фото: результат
- При выплате: "💳 200₽ отправлены на ваш счёт"

**Сервис `services/notifier.py`:**
```python
async def notify_executor(telegram_id: int, text: str, keyboard=None):
    await bot.send_message(telegram_id, text, reply_markup=keyboard)
```

#### 3.4 Баланс и выплаты
```
"Мой баланс"
  → Баланс, кол-во заданий, средний чек
  → Кнопка "Вывести" (если > 100₽)
  → Подтверждение → заявка в БД → уведомление

"Поддержка"
  → Сообщение пользователя → тикет в БД

"Пожаловаться на задание"
  → Из карточки задания → тикет с жалобой
```

---

### Фаза 4: Фронтенд — ЛК Заказчика (3-4 дня)

Берём компоненты из `retail_audit_app`, подключаем к реальному API.

**4.1 Настройка проекта**
- [ ] Новая папка `frontend/` (vite + react + tailwind + shadcn)
- [ ] Скопировать: все `ui/` компоненты, стили, theme
- [ ] Настроить axios + react-query
- [ ] Роутинг: react-router-dom

**4.2 Страницы**

```
/login             — вход (email/password)
/register          — регистрация клиента (email, пароль, компания, телефон)
/dashboard         — главная (статистика: кампании, точки, выполнено, потрачено)
/campaigns         — список кампаний
/campaigns/new     — создание кампании
/campaigns/:id     — детали кампании
/campaigns/:id/reports  — отчёты с фотографиями
```

**4.3 Создание кампании**
- Название, категория, цена за точку
- Загрузка адресов: CSV/Excel или textarea (каждый адрес с новой строки)
- Геокодирование адресов (2GIS API или Nominatim — бесплатно)
- Превью количества точек → кнопка "Опубликовать"

**4.4 Дашборд кампании**
- Прогресс-бар выполнения
- Статистика: всего / выполнено / в работе / отклонено
- Таблица точек с фото, статусом, AI-результатом, временем
- Фотогалерея (модальное окно при клике)
- Кнопка "Подтвердить" для ручной валидации
- Экспорт в CSV

**4.5 Уведомления**
- Колокольчик в хедере
- Polling `/api/notifications` каждые 30 сек (или SSE)
- Тост при новом уведомлении

---

### Фаза 5: DevOps и запуск (1-2 дня)

**5.1 docker-compose.yml**
```yaml
services:
  postgres:     # PostgreSQL 16
  backend:      # FastAPI + aiogram webhook
  frontend:     # nginx static
  nginx:        # reverse proxy
```

**5.2 .env конфигурация**
```
DATABASE_URL=postgresql+asyncpg://...
TELEGRAM_BOT_TOKEN=...
ANTHROPIC_API_KEY=...
JWT_SECRET=...
WEBHOOK_URL=https://your-domain.com/bot/webhook
MEDIA_DIR=/app/media
```

**5.3 Запуск в dev-режиме**
- `uvicorn app.main:app --reload` — бэкенд
- `vite` — фронтенд
- `ngrok` или `localtunnel` — для Telegram webhook локально

---

## Порядок разработки (рекомендуемый)

```
Неделя 1:
  День 1-2: Фаза 1.1 + 1.2 (структура, БД, авторизация)
  День 3-4: Фаза 1.3 + 1.4 (файлы, основные CRUD)
  День 5:   Фаза 2 (AI-проверка)

Неделя 2:
  День 1-4: Фаза 3 (Telegram-бот полностью)

Неделя 3:
  День 1-4: Фаза 4 (Фронтенд ЛК)
  День 5:   Фаза 5 (Docker, интеграция, тест)
```

---

## Что выходит за MVP (Версия 2+)

- Загрузка фото профиля / логотипа компании
- Фильтр заданий по расстоянию и цене
- Чат исполнитель ↔ заказчик
- История выплат с детализацией
- Настройка бюджета на месяц
- Push-уведомления (веб)
- Рейтинг исполнителей
- Интеграция с CRM ритейлера
- Автоматические выплаты (СБП API)
- Авторизация через самозанятость

---

## Открытые вопросы (нужно уточнить)

1. **Геокодирование адресов**: какой API? (2GIS — 1000 запросов/день бесплатно, Nominatim — бесплатно)
2. **Выплаты в MVP**: ручные (оператор видит заявки) или интеграция с платёжным провайдером?
3. **Регистрация заказчика**: самостоятельная или только через менеджера?
4. **Домен / хостинг**: где деплоить? (нужен HTTPS для Telegram webhook)
5. **Telegram-бот**: уже создан через BotFather? Нужен токен.
6. **Claude API**: есть ключ от Anthropic?
