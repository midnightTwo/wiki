import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2')

print("Waiting for new GitHub Actions build...")
for i in range(30):
    _, out, _ = ssh.exec_command("docker pull ghcr.io/midnighttwo/wiki-panel:latest 2>&1")
    result = out.read().decode()
    if "Downloaded newer image" in result:
        print(f"New image at {(i+1)*10}s!")
        break
    print(f"  {(i+1)*10}s...")
    time.sleep(10)
else:
    print("Timeout. Deploying current image.")

print("Deploying from /opt/wiki...")
_, out, _ = ssh.exec_command("cd /opt/wiki && docker compose pull panel 2>&1")
print(out.read().decode().strip())
_, out, _ = ssh.exec_command("cd /opt/wiki && docker compose up -d --force-recreate panel 2>&1")
print(out.read().decode().strip())

time.sleep(5)

_, out, _ = ssh.exec_command("docker exec wiki-panel-1 ls /app/frontend/dist/assets/ 2>&1")
assets = out.read().decode().strip()
print("Assets:", assets)

js = [f for f in assets.split('\n') if f.endswith('.js')][0]
_, out, _ = ssh.exec_command(f"docker exec wiki-panel-1 grep -c 'account-card' /app/frontend/dist/assets/{js} 2>&1")
print("account-card count:", out.read().decode().strip())

_, out, _ = ssh.exec_command(f"docker exec wiki-panel-1 grep -c 'multi-select\\|select-all\\|copy-selected\\|account-card-check\\|checkbox' /app/frontend/dist/assets/{js} 2>&1")
print("new features count:", out.read().decode().strip())

print("DONE!")
ssh.close()
