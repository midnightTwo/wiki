#!/bin/bash
# =====================================================
# Скрипт проверки DNS записей для komarnitsky.wiki
# Запускай после настройки DNS чтобы убедиться что всё ок
# =====================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DOMAIN="komarnitsky.wiki"
MAIL_HOST="mail.${DOMAIN}"

echo "=========================================="
echo "  Проверка DNS для ${DOMAIN}"
echo "=========================================="
echo ""

# Проверка A записи
echo -n "[A запись] mail.${DOMAIN}: "
A_RECORD=$(dig +short A ${MAIL_HOST} 2>/dev/null)
if [ -n "$A_RECORD" ]; then
    echo -e "${GREEN}✓ ${A_RECORD}${NC}"
else
    echo -e "${RED}✗ Не найдена! Добавь A запись для mail.${DOMAIN}${NC}"
fi

# Проверка MX записи
echo -n "[MX запись] ${DOMAIN}: "
MX_RECORD=$(dig +short MX ${DOMAIN} 2>/dev/null)
if [ -n "$MX_RECORD" ]; then
    echo -e "${GREEN}✓ ${MX_RECORD}${NC}"
else
    echo -e "${RED}✗ Не найдена! Добавь MX запись${NC}"
fi

# Проверка SPF
echo -n "[SPF запись] ${DOMAIN}: "
SPF_RECORD=$(dig +short TXT ${DOMAIN} 2>/dev/null | grep "spf")
if [ -n "$SPF_RECORD" ]; then
    echo -e "${GREEN}✓ ${SPF_RECORD}${NC}"
else
    echo -e "${RED}✗ Не найдена! Добавь TXT запись с v=spf1${NC}"
fi

# Проверка DKIM
echo -n "[DKIM запись] mail._domainkey.${DOMAIN}: "
DKIM_RECORD=$(dig +short TXT mail._domainkey.${DOMAIN} 2>/dev/null)
if [ -n "$DKIM_RECORD" ]; then
    echo -e "${GREEN}✓ Найдена${NC}"
else
    echo -e "${YELLOW}⚠ Не найдена (добавь после первого запуска сервера)${NC}"
fi

# Проверка DMARC
echo -n "[DMARC запись] _dmarc.${DOMAIN}: "
DMARC_RECORD=$(dig +short TXT _dmarc.${DOMAIN} 2>/dev/null)
if [ -n "$DMARC_RECORD" ]; then
    echo -e "${GREEN}✓ ${DMARC_RECORD}${NC}"
else
    echo -e "${RED}✗ Не найдена! Добавь DMARC TXT запись${NC}"
fi

# Проверка PTR (reverse DNS)
echo -n "[PTR запись] Reverse DNS: "
if [ -n "$A_RECORD" ]; then
    PTR_RECORD=$(dig +short -x ${A_RECORD} 2>/dev/null)
    if [ -n "$PTR_RECORD" ]; then
        echo -e "${GREEN}✓ ${PTR_RECORD}${NC}"
        if echo "$PTR_RECORD" | grep -q "${MAIL_HOST}"; then
            echo -e "  ${GREEN}↳ Совпадает с ${MAIL_HOST} ✓${NC}"
        else
            echo -e "  ${YELLOW}↳ Не совпадает с ${MAIL_HOST}! Настрой PTR в панели VPS${NC}"
        fi
    else
        echo -e "${RED}✗ Не найдена! Настрой Reverse DNS в панели VPS провайдера${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Пропущено (нет A записи)${NC}"
fi

# Проверка порта 25
echo -n "[Порт 25] SMTP: "
if timeout 3 bash -c "echo > /dev/tcp/${MAIL_HOST}/25" 2>/dev/null; then
    echo -e "${GREEN}✓ Открыт${NC}"
else
    echo -e "${YELLOW}⚠ Закрыт или сервер ещё не запущен${NC}"
fi

# Проверка порта 443
echo -n "[Порт 443] HTTPS: "
if timeout 3 bash -c "echo > /dev/tcp/${MAIL_HOST}/443" 2>/dev/null; then
    echo -e "${GREEN}✓ Открыт${NC}"
else
    echo -e "${YELLOW}⚠ Закрыт или сервер ещё не запущен${NC}"
fi

echo ""
echo "=========================================="
echo "  Онлайн проверка:"
echo "  https://mxtoolbox.com/?domain=${DOMAIN}"
echo "=========================================="
