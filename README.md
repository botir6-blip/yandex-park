# Yandex автопарк учун Telegram бот — MVP старт-проект

Бу архивда **интеграциясиз ишлайдиган MVP старт-кит** бор:
- Telegram бот (`aiogram 3`)
- веб админ панель (`Flask`)
- PostgreSQL schema
- база инициализация скрипти
- тест маълумотларини қўшиш скрипти
- картани шифрлаб сақлаш учун тайёр сервис

## Нима бор
- ҳайдовчини `телефон + Telegram ID` орқали боғлаш
- баланс, бонус, минимал қолдиқ
- карта қўшиш / асосий қилиш / ўчириш
- пул ечиш сўрови
- транзакциялар тарихи
- админ логин
- админда ҳайдовчилар рўйхати
- балансни қўлда тўғрилаш
- payout сўровларини қабул қилиш / рад қилиш / тўланди деб белгилаш
- созламалар

## Нима ҳали йўқ
- Yandex парк API интеграцияси
- автоматик payout
- Click/Payme интеграцияси
- SMS / 2FA
- production даражасидаги rate limit ва background worker

---

## Папкалар тузилиши

```text
yandex_park_bot_mvp/
├── app/
│   ├── admin/
│   ├── bot/
│   ├── services/
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── security.py
│   └── utils.py
├── scripts/
├── schema.sql
├── run_admin.py
├── run_bot.py
├── requirements.txt
└── .env.example
```

---

## 1. Ўрнатиш

### Python муҳит
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### `.env` тайёрлаш
`.env.example` дан нусха олинг:

```bash
cp .env.example .env
```

`CARD_ENCRYPTION_KEY` учун Fernet калит яратинг:

```bash
python scripts/generate_fernet_key.py
```

Ҳосил бўлган калитни `.env` га қўйинг.

---

## 2. PostgreSQL база тайёрлаш

Аввал PostgreSQL база яратинг, кейин `DATABASE_URL` ни `.env` га ёзинг.

Мисол:
```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/parkbot
```

### Schema қўйиш
```bash
python scripts/init_db.py
```

### Админ яратиш
```bash
python scripts/create_admin.py --login admin --password admin123 --full-name "Главный администратор"
```

### Тест ҳайдовчи қўшиш
```bash
python scripts/seed_demo_data.py
```

---

## 3. Админ панелни ишга тушириш

```bash
python run_admin.py
```

Одатда:
- URL: `http://127.0.0.1:5000`
- login: `admin`
- password: `admin123`

---

## 4. Telegram ботни ишга тушириш

`.env` га бот токенни қўйинг:
```env
BOT_TOKEN=...
```

Ишга тушириш:
```bash
python run_bot.py
```

---

## 5. Ишлаш тартиби

### Ҳайдовчи
1. `/start`
2. тил танлайди
3. телефон рақамини юборади
4. базадаги телефонга мос бўлса Telegram ID боғланади
5. кейин меню очилади

### Админ
- ҳайдовчи маълумотини кўради
- баланс қўшади/камайтиради
- payout сўровларини кўради
- статусни ўзгартиради
- созламаларни янгилайди

---

## 6. Энг муҳим жойлар

### Баланс формуласи
```text
available_to_withdraw = max(main_balance - min_reserve_balance, 0)
```

### Пополнение комиссияси
Schema ва settings'да стандарт:
```text
1%
```

### Хавфсизлик
- карта рақами тўлиқ очиқ сақланмайди
- `card_mask` алоҳида, `card_number_encrypted` алоҳида
- админ парол `werkzeug` hash билан сақланади
- муҳим амаллар `audit_logs` га ёзилади

---

## 7. Кейинги босқичда осон қўшилади
- Yandex парк `driver sync`
- автоматик payout processor
- payment callback
- background jobs
- notify/logging

---

## 8. Production'га чиқаришдан олдин нималарни қўшиш керак
- CSRF ҳимояси
- 2FA / admin login alert
- rate limit
- background worker (Celery / RQ)
- structured logging
- error monitoring
- Nginx / reverse proxy
- HTTPS
- backup strategy

---

## 9. Эслатма
Бу архив — **пухта ўйланган MVP старт-проект**.  
Яъни каркас ва асосий логика тайёр. Реал ишлаб чиқишда дизайн, интеграция ва production ҳимоялари яна кучайтирилади.


## Railway'ga joylash

Bu loyiha **bitta repo, ikkita service** ko'rinishida deploy qilinadi:
- `admin` service -> `SERVICE_TYPE=admin`
- `bot` service -> `SERVICE_TYPE=bot`

Arxiv ichida `railway.toml` va `start.sh` bor. Railway build paytida start command avtomatik olinadi.

### Railway variables
Kamida quyidagilarni qo'ying:

```env
DATABASE_URL=...
SECRET_KEY=uzun-maxfiy-qiymat
CARD_ENCRYPTION_KEY=...
BOT_TOKEN=...
SERVICE_TYPE=admin
```

Bot service uchun faqat:

```env
SERVICE_TYPE=bot
```

### Muhim
- `admin` service uchun domen ochiladi
- `bot` service uchun domen shart emas
- ikkala service ham **bir xil Postgres** ga ulangan bo'lishi kerak
