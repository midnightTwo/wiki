import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -c "admin_tags" /app/webapp/app.py', timeout=10)
print(f'admin_tags in app.py: {o.read().decode().strip()}')

_, o, _ = ssh.exec_command('docker exec wiki-panel-1 ls /app/frontend/dist/assets/', timeout=10)
assets = o.read().decode().strip()
print(f'Assets: {assets}')

for f in assets.split('\n'):
    f = f.strip()
    if f.endswith('.js'):
        _, o, _ = ssh.exec_command(f'docker exec wiki-panel-1 grep -c "tag-btn" /app/frontend/dist/assets/{f}', timeout=10)
        print(f'tag-btn in {f}: {o.read().decode().strip()}')
    if f.endswith('.css'):
        _, o, _ = ssh.exec_command(f'docker exec wiki-panel-1 grep -c "tag-btn" /app/frontend/dist/assets/{f}', timeout=10)
        print(f'tag-btn in {f}: {o.read().decode().strip()}')

ssh.close()
print('DONE')
