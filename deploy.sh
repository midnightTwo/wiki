#!/bin/bash
set -e

echo "=== [1/5] Installing Docker ==="
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker
echo "Docker $(docker --version)"

echo "=== [2/5] Installing Python + Git ==="
apt-get install -y -qq python3 python3-pip python3-venv git

echo "=== [3/5] Cloning from GitHub ==="
cd /opt
rm -rf wiki
git clone https://github.com/midnightTwo/wiki.git
cd wiki

echo "=== [4/5] Generating SECRET_KEY ==="
SECRET=$(python3 -c "import secrets; print(secrets.token_hex(16))")
sed -i "s/CHANGE_ME_GENERATE_SECRET_KEY/$SECRET/" mailu.env
echo "SECRET_KEY=$SECRET"

echo "=== [5/5] Creating directories ==="
mkdir -p /mailu/{certs,data,dkim,mail,mailqueue,filter,webmail,redis,panel-data}
mkdir -p /mailu/overrides/{nginx,dovecot,postfix,rspamd,roundcube}

echo "=== Starting Docker Compose ==="
cd /opt/wiki
docker compose up -d --build

echo "=== DONE ==="
echo "Waiting for services to start..."
sleep 15
docker compose ps
echo ""
echo "Admin panel: http://195.66.114.73:8000"
echo "Webmail: https://mail.komarnitsky.wiki/webmail"
echo ""
echo "DNS Records needed:"
echo "  A     mail.komarnitsky.wiki  ->  195.66.114.73"
echo "  MX    komarnitsky.wiki       ->  mail.komarnitsky.wiki (priority 10)"
echo "  TXT   komarnitsky.wiki       ->  v=spf1 mx a:mail.komarnitsky.wiki ~all"
