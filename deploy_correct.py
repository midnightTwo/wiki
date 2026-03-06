import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2')

# Check current compose file
_, out, _ = ssh.exec_command("cat /opt/wiki/docker-compose.yml 2>&1")
print("=== /opt/wiki/docker-compose.yml ===")
print(out.read().decode())

# Pull and recreate from correct directory
print("=== Pulling ===")
_, out, _ = ssh.exec_command("cd /opt/wiki && docker compose pull panel 2>&1")
print(out.read().decode().strip())

print("=== Recreating ===")
_, out, _ = ssh.exec_command("cd /opt/wiki && docker compose up -d --force-recreate panel 2>&1")
print(out.read().decode().strip())

time.sleep(5)

# Verify
_, out, _ = ssh.exec_command("docker exec wiki-panel-1 ls /app/frontend/dist/assets/ 2>&1")
assets = out.read().decode().strip()
print("Assets:", assets)

js_file = [f for f in assets.split('\n') if f.endswith('.js')][0]
print("JS file:", js_file)

_, out, _ = ssh.exec_command(f"docker exec wiki-panel-1 grep -oP 'sandbox.{{0,100}}' /app/frontend/dist/assets/{js_file} 2>&1")
print("Sandbox:", out.read().decode().strip())

_, out, _ = ssh.exec_command("docker inspect wiki-panel-1 --format='{{.Image}}' 2>&1")
print("Container image:", out.read().decode().strip()[:25])

ssh.close()
