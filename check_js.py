import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

checks = [
    'grep -c "allow-popups" /app/frontend/dist/assets/index-D1yG_xUo.js',
    'grep -c "base target" /app/frontend/dist/assets/index-D1yG_xUo.js',
    'grep -c "Segoe UI" /app/frontend/dist/assets/index-D1yG_xUo.js',
    'grep -c "tag-chip" /app/frontend/dist/assets/index-D1yG_xUo.js',
]
for cmd in checks:
    _, o, _ = ssh.exec_command(f'docker exec wiki-panel-1 {cmd}', timeout=10)
    print(f'{cmd.split("/")[-1].split(" ")[0] if "grep" not in cmd else cmd}: {o.read().decode().strip()}')

ssh.close()
