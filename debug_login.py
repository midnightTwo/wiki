import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

cmds = [
    'docker logs wiki-panel-1 --tail 20 2>&1',
    'grep -E "SECRET_KEY|TLS_FLAVOR|DOMAIN" /opt/wiki/mailu.env',
    'docker exec wiki-admin-1 flask mailu admin admin kmr-mail.online himarra228 2>&1',
    'docker exec wiki-admin-1 flask mailu password admin kmr-mail.online himarra228 2>&1',
]
for cmd in cmds:
    print(f'\n>>> {cmd}')
    _, o, e = ssh.exec_command(cmd, timeout=30)
    print(o.read().decode())
    print(e.read().decode())

ssh.close()
print('DONE')
