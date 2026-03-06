import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2')

# Find compose file
_, out, _ = ssh.exec_command("find / -name 'docker-compose.yml' -path '*/wiki*' 2>/dev/null")
print("Compose files:", out.read().decode().strip())

# Check container labels to see which compose file was used
_, out, _ = ssh.exec_command("docker inspect wiki-panel-1 --format='{{index .Config.Labels \"com.docker.compose.project.working_dir\"}}' 2>&1")
print("Compose working dir:", out.read().decode().strip())

_, out, _ = ssh.exec_command("docker inspect wiki-panel-1 --format='{{index .Config.Labels \"com.docker.compose.project.config_files\"}}' 2>&1")
print("Compose config:", out.read().decode().strip())

ssh.close()
