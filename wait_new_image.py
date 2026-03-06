import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2')

# Wait for truly new image
print("Waiting for new image with updated code...")
for i in range(24):
    _, out, _ = ssh.exec_command("docker pull ghcr.io/midnighttwo/wiki-panel:latest 2>&1")
    result = out.read().decode()
    if "Downloaded newer image" in result:
        print(f"  NEW image downloaded at {(i+1)*10}s!")
        
        # Recreate
        _, out, _ = ssh.exec_command("cd /root/wiki && docker compose up -d --force-recreate panel 2>&1")
        print(out.read().decode())
        time.sleep(5)
        
        # Verify
        _, out, _ = ssh.exec_command("docker exec wiki-panel-1 ls /app/frontend/dist/assets/ 2>&1")
        print("Assets:", out.read().decode().strip())
        
        js_files = out.read().decode().strip() if out else ""
        # Find JS file
        _, out, _ = ssh.exec_command("docker exec wiki-panel-1 ls /app/frontend/dist/assets/ 2>&1")
        assets = out.read().decode().strip().split('\n')
        js_file = [f for f in assets if f.endswith('.js')][0]
        
        _, out, _ = ssh.exec_command(f"docker exec wiki-panel-1 grep -oP 'sandbox.{{0,100}}' /app/frontend/dist/assets/{js_file} 2>&1")
        print("Sandbox:", out.read().decode().strip())
        
        print("DONE!")
        ssh.close()
        exit()
    
    print(f"  {(i+1)*10}s - still waiting...")
    time.sleep(10)

print("No new image after 4 minutes. GitHub Actions may not have triggered.")
ssh.close()
