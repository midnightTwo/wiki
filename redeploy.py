import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2')

# Remove old container, pull fresh, recreate
print("Stopping and removing panel container...")
_, out, _ = ssh.exec_command("cd /root/wiki && docker compose stop panel && docker compose rm -f panel 2>&1")
print(out.read().decode().strip())

print("\nPulling fresh image...")
_, out, _ = ssh.exec_command("docker pull ghcr.io/midnighttwo/wiki-panel:latest 2>&1")
print(out.read().decode().strip())

print("\nStarting panel...")
_, out, _ = ssh.exec_command("cd /root/wiki && docker compose up -d panel 2>&1")
print(out.read().decode().strip())

time.sleep(5)

# Check assets
_, out, _ = ssh.exec_command("docker exec wiki-panel-1 ls /app/frontend/dist/assets/ 2>&1")
assets = out.read().decode().strip()
print("\nAssets:", assets)

# Find JS file
js_file = [f for f in assets.split('\n') if f.endswith('.js')][0]
print("JS file:", js_file)

_, out, _ = ssh.exec_command(f"docker exec wiki-panel-1 grep -oP 'sandbox.{{0,100}}' /app/frontend/dist/assets/{js_file} 2>&1")
print("Sandbox:", out.read().decode().strip())

# Check container image
_, out, _ = ssh.exec_command("docker inspect wiki-panel-1 --format='{{.Image}}' 2>&1")
print("Container image:", out.read().decode().strip()[:20])

ssh.close()
