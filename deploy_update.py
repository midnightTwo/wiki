import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

# Wait for GitHub Actions build (check every 15s)
print('Waiting for new image on GHCR...')
# Get current image ID
_, o, _ = ssh.exec_command('docker images ghcr.io/midnighttwo/wiki-panel:latest --format "{{.ID}}"', timeout=10)
old_id = o.read().decode().strip()
print(f'Current image: {old_id}')

for i in range(20):
    time.sleep(15)
    _, o, _ = ssh.exec_command('docker pull ghcr.io/midnighttwo/wiki-panel:latest 2>&1 | tail -3', timeout=60)
    out = o.read().decode()
    print(f'Attempt {i+1}: {out.strip()}')
    if 'Downloaded newer image' in out or 'Image is up to date' in out:
        _, o2, _ = ssh.exec_command('docker images ghcr.io/midnighttwo/wiki-panel:latest --format "{{.ID}}"', timeout=10)
        new_id = o2.read().decode().strip()
        if new_id != old_id or i > 5:
            print(f'New image ready: {new_id}')
            break

# Restart panel
print('\nRestarting panel...')
_, o, e = ssh.exec_command('cd /opt/wiki && docker compose up -d panel', timeout=60)
print(e.read().decode())

time.sleep(5)

# Check
_, o, _ = ssh.exec_command('docker logs wiki-panel-1 --tail 5 2>&1', timeout=10)
print(f'\nPanel logs:\n{o.read().decode()}')

ssh.close()
print('DONE')
