import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

cmds = [
    'cd /opt/wiki && git reset --hard HEAD && git clean -fd && git pull origin main 2>&1',
    'cd /opt/wiki && grep -A3 "panel:" docker-compose.yml | head -5',
    'cd /opt/wiki && docker compose stop panel && docker compose rm -f panel && docker compose up -d panel 2>&1',
    'sleep 4 && docker logs wiki-panel-1 --tail 5 2>&1',
]
for cmd in cmds:
    print(f'\n>>> {cmd}')
    _, o, e = ssh.exec_command(cmd, timeout=120)
    ot = o.read().decode().strip()
    et = e.read().decode().strip()
    if ot: print(ot)
    if et: print(et)

ssh.close()
print('\nDONE!')
