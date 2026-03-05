#!/bin/bash
# =====================================================
# Скрипт установки Mailu Mail Server
# Для komarnitsky.wiki
# Запускай на VPS с Ubuntu 22.04/24.04 или Debian 12
# =====================================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Установка почтового сервера Mailu          ║${NC}"
echo -e "${BLUE}║   Домен: komarnitsky.wiki                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ---- Проверки ----
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ОШИБКА] Запусти скрипт от root: sudo bash setup.sh${NC}"
    exit 1
fi

# Получаем IP сервера
SERVER_IP=$(curl -s4 ifconfig.me)
echo -e "${GREEN}[✓] IP сервера: ${SERVER_IP}${NC}"

# ---- Шаг 1: Обновление системы ----
echo -e "\n${YELLOW}[1/6] Обновление системы...${NC}"
apt-get update -qq
apt-get upgrade -y -qq

# ---- Шаг 2: Установка Docker ----
echo -e "\n${YELLOW}[2/6] Установка Docker...${NC}"

if command -v docker &> /dev/null; then
    echo -e "${GREEN}[✓] Docker уже установлен${NC}"
else
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo -e "${GREEN}[✓] Docker установлен${NC}"
fi

# Проверяем Docker Compose
if docker compose version &> /dev/null; then
    echo -e "${GREEN}[✓] Docker Compose доступен${NC}"
else
    echo -e "${RED}[ОШИБКА] Docker Compose не найден${NC}"
    exit 1
fi

# ---- Шаг 3: Настройка фаервола ----
echo -e "\n${YELLOW}[3/6] Настройка фаервола...${NC}"

# Установить ufw если нет
apt-get install -y -qq ufw

ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 25/tcp    # SMTP
ufw allow 465/tcp   # SMTPS
ufw allow 587/tcp   # Submission
ufw allow 993/tcp   # IMAPS
ufw allow 995/tcp   # POP3S (опционально)

ufw --force enable
echo -e "${GREEN}[✓] Фаервол настроен${NC}"

# ---- Шаг 4: Создание директорий ----
echo -e "\n${YELLOW}[4/6] Создание директорий...${NC}"

mkdir -p /mailu/{data,dkim,mail,mailqueue,filter,webmail,redis,certs}
mkdir -p /mailu/overrides/{nginx,dovecot,postfix,rspamd,roundcube}

echo -e "${GREEN}[✓] Директории созданы${NC}"

# ---- Шаг 5: Генерация секретного ключа ----
echo -e "\n${YELLOW}[5/6] Генерация конфигурации...${NC}"

SECRET=$(python3 -c "import secrets; print(secrets.token_hex(16))" 2>/dev/null || openssl rand -hex 16)

# Если файлы ещё не скопированы, напоминаем
if [ ! -f /mailu/docker-compose.yml ]; then
    echo -e "${YELLOW}[!] Скопируй файлы проекта в /mailu/:${NC}"
    echo -e "    scp docker-compose.yml mailu.env root@${SERVER_IP}:/mailu/"
    echo ""
fi

# Обновляем секретный ключ в mailu.env если файл существует
if [ -f /mailu/mailu.env ]; then
    sed -i "s/SECRET_KEY=CHANGE_ME_GENERATE_SECRET_KEY/SECRET_KEY=${SECRET}/" /mailu/mailu.env
    echo -e "${GREEN}[✓] Секретный ключ сгенерирован${NC}"
fi

echo -e "${GREEN}[✓] Секретный ключ: ${SECRET}${NC}"
echo -e "${YELLOW}    Сохрани его! Если потеряешь — сгенерируй новый${NC}"

# ---- Шаг 6: Настройка hostname ----
echo -e "\n${YELLOW}[6/6] Настройка hostname...${NC}"

hostnamectl set-hostname mail.komarnitsky.wiki
echo -e "${GREEN}[✓] Hostname установлен: mail.komarnitsky.wiki${NC}"

# ---- Итог ----
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Установка завершена! Следующие шаги:               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}1. Скопируй файлы на сервер:${NC}"
echo -e "   scp docker-compose.yml mailu.env root@${SERVER_IP}:/mailu/"
echo ""
echo -e "${GREEN}2. Замени в mailu.env:${NC}"
echo -e "   - SECRET_KEY (уже сгенерирован если запустил setup.sh)"
echo -e "   - INITIAL_ADMIN_PW — пароль для админки"
echo ""
echo -e "${GREEN}3. Настрой DNS записи (см. README.md)${NC}"
echo ""
echo -e "${GREEN}4. Запусти почтовый сервер:${NC}"
echo -e "   cd /mailu && docker compose up -d"
echo ""
echo -e "${GREEN}5. Создай админа:${NC}"
echo -e "   docker compose -f /mailu/docker-compose.yml exec admin flask mailu admin admin komarnitsky.wiki ТВОЙ_ПАРОЛЬ"
echo ""
echo -e "${GREEN}6. Открой в браузере:${NC}"
echo -e "   Админка:  https://mail.komarnitsky.wiki/admin"
echo -e "   Webmail:  https://mail.komarnitsky.wiki/webmail"
echo ""
echo -e "${YELLOW}[!] Подожди 2-3 минуты после запуска — Let's Encrypt получит сертификат${NC}"
echo -e "${YELLOW}[!] DKIM ключ появится в /mailu/dkim/ — добавь его в DNS${NC}"
