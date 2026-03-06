import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2')

js = "/app/frontend/dist/assets/index-D1yG_xUo.js"

# Search for sandbox anywhere
_, out, _ = ssh.exec_command(f"docker exec wiki-panel-1 grep -oP 'sandbox.{{0,100}}' {js} 2>&1")
print("sandbox context:", out.read().decode().strip())

# Search for allow-popups
_, out, _ = ssh.exec_command(f"docker exec wiki-panel-1 grep -c 'allow-popups' {js} 2>&1")
print("allow-popups count:", out.read().decode().strip())

# Check if wrapHtml has the html test  
_, out, _ = ssh.exec_command(f"docker exec wiki-panel-1 grep -oP 'test\\(.{{0,30}}' {js} 2>&1 | head -5")
print("test() calls:", out.read().decode().strip())

# Recreate with force and new image
print("\n--- Force recreating panel ---")
_, out, _ = ssh.exec_command("cd /root/wiki && docker compose down panel && docker compose up -d panel 2>&1")
print(out.read().decode().strip())

import time
time.sleep(5)

# Check assets after recreate
_, out, _ = ssh.exec_command("docker exec wiki-panel-1 ls /app/frontend/dist/assets/ 2>&1")
print("\nNew assets:", out.read().decode().strip())

ssh.close()
