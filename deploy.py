import paramiko
import sys
import time

for attempt in range(5):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f'Connecting... attempt {attempt+1}')
        ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)
        print('Connected!')
        break
    except Exception as e:
        print(f'Failed: {e}')
        if attempt < 4:
            time.sleep(5)
        else:
            print('Could not connect after 5 attempts')
            sys.exit(1)

commands = [
    "cd /opt/wiki && sed -i '/<<<<<<</d; /=======/d; />>>>>>>/d' docker-compose.yml",
    "cd /opt/wiki && sed -i 's|DB_PATH=/data/komarnitsky-mail.db|DB_PATH=/data/panel.db|' docker-compose.yml",
    "cd /opt/wiki && head -5 docker-compose.yml",
    "cd /opt/wiki && docker compose stop panel 2>&1",
    "cd /opt/wiki && docker compose rm -f panel 2>&1",
    "cd /opt/wiki && docker compose up -d panel 2>&1",
    "sleep 5 && docker ps --format '{{.Names}} {{.Status}}' | grep panel",
    "sleep 2 && docker logs wiki-panel-1 --tail 5 2>&1",
]

for cmd in commands:
    print(f'\n>>> {cmd}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out: print(out)
    if err: print(err)

ssh.close()
print('\nDone!')
