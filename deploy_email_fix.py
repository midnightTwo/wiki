import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2')

# Wait for new image
print("Waiting for GitHub Actions build...")
for i in range(30):
    _, out, _ = ssh.exec_command("docker pull ghcr.io/midnighttwo/wiki-panel:latest 2>&1")
    result = out.read().decode()
    if "Downloaded newer image" in result:
        print(f"New image pulled after {(i+1)*10}s!")
        break
    print(f"  {(i+1)*10}s - still building...")
    time.sleep(10)
else:
    print("Timeout waiting for new image. Deploying anyway.")

# Recreate panel
print("\nRestarting panel...")
_, out, _ = ssh.exec_command("cd /root/wiki && docker compose up -d --force-recreate panel 2>&1")
print(out.read().decode())

time.sleep(3)

# Verify new code
print("\nVerifying...")
_, out, _ = ssh.exec_command("docker exec wiki-panel-1 grep -c 'allow-popups-to-escape-sandbox' /app/frontend/dist/assets/*.js 2>/dev/null || echo 'NOT FOUND'")
v = out.read().decode().strip()
print(f"  allow-popups-to-escape-sandbox in JS: {v}")

_, out, _ = ssh.exec_command("docker exec wiki-panel-1 grep -c 'HAS_HTML_TAG' /app/frontend/dist/assets/*.js 2>/dev/null || echo 'NOT FOUND'")
v2 = out.read().decode().strip()
print(f"  wrapHtml fix marker (test regex): checking for '<html' detection")

_, out, _ = ssh.exec_command(r"docker exec wiki-panel-1 grep -c '<html' /app/frontend/dist/assets/*.js 2>/dev/null || echo 'NOT FOUND'")
v3 = out.read().decode().strip()
print(f"  <html regex in JS: {v3}")

print("\nDone!")
ssh.close()
