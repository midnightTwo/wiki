import paramiko, time

for attempt in range(30):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)
        
        _, o, _ = ssh.exec_command('docker pull ghcr.io/midnighttwo/wiki-panel:latest 2>&1 | tail -3', timeout=120)
        out = o.read().decode().strip()
        print(f'Attempt {attempt+1}: {out}')
        
        if 'Downloaded newer image' in out:
            print('NEW IMAGE!')
            _, o, e = ssh.exec_command('cd /opt/wiki && docker compose up -d panel', timeout=60)
            print(e.read().decode())
            time.sleep(5)
            _, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -c "account-select" /app/frontend/dist/assets/*.js 2>/dev/null || echo NOT_FOUND', timeout=10)
            print(f'account-select in JS: {o.read().decode().strip()}')
            ssh.close()
            print('DONE')
            break
        
        ssh.close()
        if attempt > 12:
            print('Still no new image after 3+ min, checking Actions...')
            break
        time.sleep(15)
    except Exception as ex:
        print(f'Attempt {attempt+1} error: {ex}')
        time.sleep(15)
