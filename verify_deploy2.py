import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2')

# Check container is running
_, out, _ = ssh.exec_command("docker ps --filter name=wiki-panel-1 --format '{{.Status}}' 2>&1")
print("Panel status:", out.read().decode().strip())

# Check JS files  
_, out, _ = ssh.exec_command("docker exec wiki-panel-1 ls /app/frontend/dist/assets/ 2>&1")
print("Assets:", out.read().decode().strip())

# Check for new sandbox
_, out, _ = ssh.exec_command("docker exec wiki-panel-1 grep -o 'allow-popups[^ \"]*' /app/frontend/dist/assets/*.js 2>&1")
print("Sandbox attrs:", out.read().decode().strip())

# Check for html detection regex in wrapHtml
_, out, _ = ssh.exec_command("docker exec wiki-panel-1 grep -o 'html.*test' /app/frontend/dist/assets/*.js 2>&1 | head -3")
print("HTML test:", out.read().decode().strip())

# Check for baseTag variable or similar
_, out, _ = ssh.exec_command(r"docker exec wiki-panel-1 grep -c 'escape-sandbox' /app/frontend/dist/assets/*.js 2>&1")
print("escape-sandbox count:", out.read().decode().strip())

# Get a snippet around sandbox
_, out, _ = ssh.exec_command(r"docker exec wiki-panel-1 grep -oP 'sandbox=.{0,80}' /app/frontend/dist/assets/*.js 2>&1")
print("Sandbox snippet:", out.read().decode().strip())

ssh.close()
