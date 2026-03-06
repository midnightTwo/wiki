import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

# Get accounts list from DB  
_, o, _ = ssh.exec_command("docker exec wiki-panel-1 python3 -c \"import sqlite3; db=sqlite3.connect('/data/panel.db'); [print(r[0],r[1]) for r in db.execute('SELECT email,password FROM generated_accounts')]\"", timeout=10)
print("Accounts:")
print(o.read().decode())

ssh.close()
