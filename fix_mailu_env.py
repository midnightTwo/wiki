import paramiko, secrets

secret_key = secrets.token_hex(16)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

cmds = [
    # Fix SECRET_KEY
    f"sed -i 's/^SECRET_KEY=.*/SECRET_KEY={secret_key}/' /opt/wiki/mailu.env",
    # Fix TLS_FLAVOR
    "sed -i 's/^TLS_FLAVOR=.*/TLS_FLAVOR=notls/' /opt/wiki/mailu.env",
    # Verify changes
    "grep -E 'SECRET_KEY|TLS_FLAVOR' /opt/wiki/mailu.env",
    # Restart all containers
    "cd /opt/wiki && docker compose down && docker compose pull panel && docker compose up -d",
]

for cmd in cmds:
    print(f'\n>>> {cmd}')
    _, o, e = ssh.exec_command(cmd, timeout=120)
    print(o.read().decode())
    err = e.read().decode()
    if err:
        print(f'STDERR: {err}')

# Wait and check
import time
time.sleep(10)
_, o, e = ssh.exec_command('docker ps --format "{{.Names}}: {{.Status}}" | sort', timeout=30)
print('\n>>> Container status:')
print(o.read().decode())

# Check panel logs
_, o, e = ssh.exec_command('docker logs wiki-panel-1 --tail 10 2>&1', timeout=15)
print('\n>>> Panel logs:')
print(o.read().decode())

ssh.close()
print('\nDONE')
