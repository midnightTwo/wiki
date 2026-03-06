import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2')

# Use the actual filename
js = "/app/frontend/dist/assets/index-D1yG_xUo.js"

_, out, _ = ssh.exec_command(f"docker exec wiki-panel-1 grep -o 'sandbox=.[^\"]*' {js} 2>&1")
print("Sandbox:", out.read().decode().strip())

_, out, _ = ssh.exec_command(f"docker exec wiki-panel-1 grep -c 'escape' {js} 2>&1")
print("escape count:", out.read().decode().strip())

# Check image ID
_, out, _ = ssh.exec_command("docker images ghcr.io/midnighttwo/wiki-panel:latest --format '{{.ID}} {{.CreatedAt}}' 2>&1")
print("Image:", out.read().decode().strip())

# Maybe image wasn't updated - let's force pull again
_, out, _ = ssh.exec_command("docker pull ghcr.io/midnighttwo/wiki-panel:latest 2>&1 | tail -5")
print("Pull result:", out.read().decode().strip())

ssh.close()
