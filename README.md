# ClinicIncomeBot

Telegram-бот для учёта дохода от первичных и вторичных приёмов в нескольких поликлиниках.

Бот не хранит имена пациентов, телефоны, диагнозы и другие медицинские или персональные данные. В базе сохраняются только поликлиника, тип приёма, сумма и дата.

## Возможности

- добавление поликлиник;
- отдельная цена первичного и вторичного приёма;
- быстрое добавление приёма готовой кнопкой;
- статистика за сегодня;
- статистика за текущий месяц;
- статистика за выбранный период через календарь;
- удаление последнего ошибочного приёма;
- изменение цен без изменения сумм старых записей;
- доступ только для двух разрешённых Telegram-аккаунтов;
- оба разрешённых аккаунта имеют права администратора;
- ежедневные резервные копии SQLite;
- автоматический запуск на Ubuntu через systemd.

## Стек

- Python 3.11+;
- aiogram 3;
- SQLite;
- aiosqlite;
- python-dotenv;
- Ubuntu 24.04;
- systemd.

## Структура проекта

```text
ClinicIncomeBot/
├── database/       # Работа с SQLite
├── handlers/       # Обработчики команд, сообщений и кнопок
├── keyboards/      # Клавиатуры Telegram
├── middlewares/    # Проверка доступа
├── states/         # Состояния диалогов FSM
├── scripts/        # Резервное копирование базы
├── deploy/         # Примеры файлов systemd
├── config.py       # Загрузка настроек из .env
├── main.py         # Точка запуска бота
├── requirements.txt
├── .env.example
└── .gitignore
```

## Локальный запуск на Windows

Создайте виртуальное окружение:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Создайте `.env` на основе `.env.example`:

```env
BOT_TOKEN=your_bot_token
ADMIN_ID=first_allowed_telegram_id
USER_ID=second_allowed_telegram_id
```

Запустите бота:

```powershell
.\venv\Scripts\python.exe .\main.py
```

## Запуск на Ubuntu 24.04

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

cd /opt/clinic-income-bot
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
```

После создания `.env` можно использовать примеры служб из папки `deploy`.

```bash
sudo cp deploy/clinic-income-bot.service.example \
    /etc/systemd/system/clinic-income-bot.service

sudo cp deploy/clinic-income-backup.service.example \
    /etc/systemd/system/clinic-income-backup.service

sudo cp deploy/clinic-income-backup.timer.example \
    /etc/systemd/system/clinic-income-backup.timer

sudo systemctl daemon-reload
sudo systemctl enable --now clinic-income-bot.service
sudo systemctl enable --now clinic-income-backup.timer
```

Проверка:

```bash
systemctl status clinic-income-bot.service
journalctl -u clinic-income-bot.service -n 50 --no-pager
```

## Безопасность

Никогда не публикуйте:

- `.env`;
- токен Telegram-бота;
- Telegram ID владельцев;
- `clinic_income.db`;
- резервные копии базы;
- приватные SSH-ключи.

Эти файлы исключены через `.gitignore`.