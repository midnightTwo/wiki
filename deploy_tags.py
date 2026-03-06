import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

_, o, _ = ssh.exec_command('docker images ghcr.io/midnighttwo/wiki-panel:latest --format "{{.ID}}"', timeout=10)
old_id = o.read().decode().strip()
print(f'Current: {old_id}')

for i in range(20):
    time.sleep(20)
    try:
        _, o, _ = ssh.exec_command('docker pull ghcr.io/midnighttwo/wiki-panel:latest 2>&1 | tail -3', timeout=120)
        out = o.read().decode().strip()
        print(f'[{i+1}] {out}')
        if 'Downloaded newer image' in out:
            break
    except:
        ssh.close()
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)
        print(f'[{i+1}] reconnected')

_, _, e = ssh.exec_command('cd /opt/wiki && docker compose up -d panel 2>&1', timeout=60)
print(f'\n{e.read().decode().strip()}')
time.sleep(5)

_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -c "tag-btn" /app/frontend/dist/assets/*.css 2>/dev/null; docker exec wiki-panel-1 grep -c "admin_tags" /app/webapp/app.py', timeout=10)
print(f'\nVerify: {o.read().decode().strip()}')

ssh.close()
print('DONE')
