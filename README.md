# Почтовый сервер Komarnitsky Mail

## komarnitsky.wiki — свой почтовый сервер с админкой

Полноценный почтовый сервер на базе **Mailu** с:
- **Админкой** — создавай/удаляй почтовые ящики через веб-интерфейс
- **Webmail** — пользователи входят через браузер (Roundcube)
- **Антиспам** — Rspamd фильтрует спам автоматически
- **DKIM/SPF/DMARC** — письма не попадают в спам у получателей
- **Let's Encrypt** — автоматический SSL сертификат

---

## 📋 Что нужно

1. **VPS сервер** (минимум 2 ГБ RAM, 20 ГБ диска)
   - Рекомендуемые: [Hetzner](https://www.hetzner.com/cloud) (€3.79/мес), [Contabo](https://contabo.com) ($4.99/мес)
   - ОС: Ubuntu 22.04 или 24.04
   - **ВАЖНО:** VPS должен разрешать порт 25 (некоторые провайдеры блокируют)

2. **Домен** komarnitsky.wiki (уже есть)

3. **Доступ к DNS** (через регистратор домена или Cloudflare)

---

## 🚀 Установка (пошагово)

### Шаг 1: Купи VPS

Рекомендую **Hetzner Cloud**:
1. Зарегистрируйся на [hetzner.com](https://www.hetzner.com/cloud)
2. Создай сервер: **CX22** (2 vCPU, 4 GB RAM) — €5.39/мес
3. ОС: **Ubuntu 24.04**
4. Добавь SSH ключ (или запомни root пароль)
5. Запиши **IP адрес** сервера

### Шаг 2: Настрой DNS

Зайди в панель управления DNS твоего домена и добавь эти записи:

> **ЗАМЕНИ `YOUR_SERVER_IP` на реальный IP твоего VPS!**

| Тип | Имя | Значение | Приоритет | TTL |
|-----|------|----------|-----------|-----|
| **A** | `mail` | `YOUR_SERVER_IP` | — | 3600 |
| **A** | `@` | `YOUR_SERVER_IP` | — | 3600 |
| **MX** | `@` | `mail.komarnitsky.wiki` | 10 | 3600 |
| **TXT** | `@` | `v=spf1 mx a:mail.komarnitsky.wiki ~all` | — | 3600 |
| **TXT** | `_dmarc` | `v=DMARC1; p=reject; rua=mailto:admin@komarnitsky.wiki; ruf=mailto:admin@komarnitsky.wiki; adkim=s; aspf=s` | — | 3600 |
| **TXT** | `mail._domainkey` | *(добавишь после первого запуска — см. Шаг 6)* | — | 3600 |

**Также настрой Reverse DNS (PTR запись):**
- В панели Hetzner → выбери сервер → Networking → Reverse DNS
- Установи: `mail.komarnitsky.wiki`

### Шаг 3: Подключись к серверу

```bash
ssh root@YOUR_SERVER_IP
```

### Шаг 4: Запусти установщик

```bash
# Скачай файлы или скопируй их на сервер
mkdir -p /mailu
cd /mailu

# Вариант 1: Скопируй файлы с компа (запусти на СВОЁМ компе)
scp docker-compose.yml mailu.env setup.sh root@YOUR_SERVER_IP:/mailu/

# Вариант 2: Или создай файлы прямо на сервере через nano
```

Затем на сервере:

```bash
cd /mailu
chmod +x setup.sh
bash setup.sh
```

### Шаг 5: Настрой конфигурацию

Отредактируй `/mailu/mailu.env`:

```bash
nano /mailu/mailu.env
```

**Обязательно измени:**
- `SECRET_KEY` — уникальный ключ (setup.sh генерирует автоматически)
- `INITIAL_ADMIN_PW` — пароль для входа в админку

### Шаг 6: Запусти сервер

```bash
cd /mailu
docker compose up -d
```

Подожди 2-3 минуты, пока сервер запустится и получит SSL сертификат.

### Шаг 7: Создай админа

```bash
docker compose exec admin flask mailu admin admin komarnitsky.wiki ТВОЙ_НАДЁЖНЫЙ_ПАРОЛЬ
```

### Шаг 8: Добавь DKIM в DNS

```bash
# Посмотри DKIM ключ:
cat /mailu/dkim/komarnitsky.wiki.mail.key

# Или так:
docker compose exec admin cat /dkim/komarnitsky.wiki.mail.key
```

Скопируй содержимое и добавь TXT запись в DNS:
- **Имя:** `mail._domainkey`
- **Значение:** содержимое файла (начинается с `v=DKIM1; k=rsa; p=...`)

---

## 🖥️ Использование

### Админка (для тебя)

**URL:** `https://mail.komarnitsky.wiki/admin`

Здесь ты можешь:
- ✅ Создавать новые почтовые ящики (например, `user@komarnitsky.wiki`)
- ✅ Удалять ящики
- ✅ Менять пароли пользователей
- ✅ Настраивать алиасы (пересылку)
- ✅ Устанавливать квоты (ограничение размера ящика)
- ✅ Смотреть статистику

### Webmail (для пользователей)

**URL:** `https://mail.komarnitsky.wiki/webmail`

Пользователи входят с:
- **Логин:** `user@komarnitsky.wiki`
- **Пароль:** тот, что ты установил при создании ящика

### Подключение через почтовый клиент (Outlook, Thunderbird, телефон)

| Протокол | Сервер | Порт | Шифрование |
|----------|--------|------|------------|
| IMAP | mail.komarnitsky.wiki | 993 | SSL/TLS |
| SMTP | mail.komarnitsky.wiki | 587 | STARTTLS |
| POP3 | mail.komarnitsky.wiki | 995 | SSL/TLS |

---

## 🔧 Полезные команды

```bash
# Статус контейнеров
docker compose ps

# Логи (все)
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f smtp
docker compose logs -f imap

# Перезапуск
docker compose restart

# Остановить
docker compose down

# Обновить (новая версия Mailu)
docker compose pull
docker compose up -d

# Создать нового пользователя из командной строки
docker compose exec admin flask mailu user username komarnitsky.wiki 'password123'

# Сменить пароль пользователю
docker compose exec admin flask mailu password username komarnitsky.wiki 'new_password'

# Удалить пользователя
docker compose exec admin flask mailu user-delete username@komarnitsky.wiki

# Бэкап данных
tar -czf /backup/mailu-$(date +%Y%m%d).tar.gz /mailu/
```

---

## 🛡️ Проверка работоспособности

После установки проверь:

1. **MX записи:** https://mxtoolbox.com/ — введи `komarnitsky.wiki`
2. **SPF:** https://mxtoolbox.com/spf.aspx — проверь SPF запись
3. **DKIM:** https://mxtoolbox.com/dkim.aspx — введи `mail` и `komarnitsky.wiki`
4. **Доставляемость:** отправь письмо на https://mail-tester.com — должно быть 9-10/10
5. **SSL:** https://www.ssllabs.com/ssltest/ — проверь `mail.komarnitsky.wiki`

---

## ⚠️ Частые проблемы

### Письма не приходят
- Проверь MX запись: `dig MX komarnitsky.wiki`
- Проверь порт 25: `telnet mail.komarnitsky.wiki 25`
- Логи: `docker compose logs smtp`

### Письма уходят в спам
- Убедись что DKIM добавлен в DNS
- Проверь PTR запись (Reverse DNS)
- Проверь SPF и DMARC записи
- Протестируй на mail-tester.com

### Не получается войти в админку
- Убедись что контейнеры запущены: `docker compose ps`
- Проверь что создал админа: 
  ```bash
  docker compose exec admin flask mailu admin admin komarnitsky.wiki PASSWORD
  ```

### Let's Encrypt не выдаёт сертификат
- DNS запись `mail.komarnitsky.wiki` должна указывать на IP сервера
- Порт 80 должен быть открыт
- Подожди 5-10 минут после изменения DNS

---

## 📁 Структура файлов на сервере

```
/mailu/
├── docker-compose.yml    # Конфигурация контейнеров
├── mailu.env             # Настройки почтового сервера
├── setup.sh              # Скрипт установки
├── data/                 # Данные админки
├── dkim/                 # DKIM ключи
├── mail/                 # Почтовые ящики (письма)
├── mailqueue/            # Очередь отправки
├── filter/               # Данные антиспама
├── webmail/              # Данные Roundcube
├── redis/                # Кэш Redis
├── certs/                # SSL сертификаты
└── overrides/            # Кастомные настройки
    ├── nginx/
    ├── dovecot/
    ├── postfix/
    ├── rspamd/
    └── roundcube/
```

---

## 💰 Стоимость

| Что | Сколько |
|-----|---------|
| VPS (Hetzner CX22) | ~€5.39/мес (~$6/мес) |
| Домен komarnitsky.wiki | ~$1-15/год (зависит от регистратора) |
| SSL сертификат | Бесплатно (Let's Encrypt) |
| **Итого** | **~$6-7/мес** |

---

## 🔄 Автоматические бэкапы (рекомендуется)

Создай cron задачу для ежедневного бэкапа:

```bash
# Открой crontab
crontab -e

# Добавь строку (бэкап каждый день в 3:00):
0 3 * * * tar -czf /backup/mailu-$(date +\%Y\%m\%d).tar.gz /mailu/ && find /backup/ -name "mailu-*.tar.gz" -mtime +7 -delete
```

Не забудь создать папку: `mkdir -p /backup`
