import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

# Check if refresh-btn exists in built JS
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -l "refresh-btn" /app/frontend/dist/assets/*.js 2>&1', timeout=10)
print(f'Refresh in JS: {o.read().decode().strip()}')

# Check if del-mail-btn exists
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -l "del-mail-btn" /app/frontend/dist/assets/*.js 2>&1', timeout=10)
print(f'Delete in JS: {o.read().decode().strip()}')

# Check if api_mail_delete exists in backend
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep "DELETE" /app/webapp/app.py 2>&1', timeout=10)
print(f'DELETE route: {o.read().decode().strip()}')

# Check what JS files are served
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 ls -la /app/frontend/dist/assets/', timeout=10)
print(f'\nAssets:\n{o.read().decode()}')

ssh.close()
