import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

_, o, _ = ssh.exec_command('docker exec wiki-panel-1 ls /app/frontend/dist/assets/', timeout=10)
print('Assets:', o.read().decode())

# Check CSS for refresh
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -c "refresh" /app/frontend/dist/assets/index-B4u21ity.css', timeout=10)
print('refresh in CSS:', o.read().decode().strip())

# Find JS files
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 find /app/frontend/dist/assets -name "*.js"', timeout=10)
js_files = o.read().decode().strip().split('\n')
print('JS files:', js_files)

for f in js_files:
    _, o, _ = ssh.exec_command(f'docker exec wiki-panel-1 grep -c "Refresh" {f}', timeout=10)
    print(f'  {f} -> Refresh count: {o.read().decode().strip()}')

# Check if frontend source has the changes
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 cat /app/frontend/dist/index.html', timeout=10)
print('\nindex.html:', o.read().decode())

ssh.close()
