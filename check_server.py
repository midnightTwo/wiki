import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2')
# Check mailu.env SECRET_KEY and try to rebuild
cmds = """
echo "=== TEST PANEL (port 8000) ==="
curl -s -o /dev/null -w "HTTP %{http_code}" http://127.0.0.1:8000/ 2>&1
echo ""
echo "=== TEST MAILU FRONT (port 80) ==="
curl -s -o /dev/null -w "HTTP %{http_code}" http://127.0.0.1:80/ 2>&1
echo ""
echo "=== PANEL RESPONSE ==="
curl -s http://127.0.0.1:8000/ 2>&1 | head -5
echo ""
echo "=== PANEL LOGS ==="
docker compose logs panel 2>&1 | tail -15
echo "=== FRONT LOGS ==="
docker compose logs front 2>&1 | tail -10
echo "=== DONE ==="
"""
stdin, stdout, stderr = c.exec_command(f'cd /opt/wiki && {cmds}')
out = stdout.read().decode()
print(out)
err = stderr.read().decode()
if err:
    print("STDERR:", err)
c.close()
