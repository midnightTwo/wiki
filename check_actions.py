import urllib.request, json

r = urllib.request.urlopen('https://api.github.com/repos/midnightTwo/wiki/actions/runs?per_page=5')
data = json.loads(r.read())
for run in data['workflow_runs']:
    print(f"{run['id']} | {run['status']} | {run['conclusion']} | {run['head_sha'][:8]} | {run['created_at']}")
