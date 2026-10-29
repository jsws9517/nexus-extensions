import requests, subprocess, sys

token = subprocess.check_output(['gh', 'auth', 'token']).decode().strip()

releases = requests.get('https://api.github.com/repos/jsws9517/paddle-ocr/releases',
    headers={'Authorization': f'token {token}'}).json()
release_id = releases[0]['id']
print(f'Release ID: {release_id}')

url = f'https://uploads.github.com/repos/jsws9517/paddle-ocr/releases/{release_id}/assets?name=paddle-ocr.zip'
print(f'Uploading paddle-ocr.zip (90MB)...')

with open('D:/agent-cli/paddle-standalone/paddle-ocr.zip', 'rb') as f:
    resp = requests.post(url,
        headers={'Authorization': f'token {token}', 'Content-Type': 'application/zip'},
        data=f,
        timeout=600)

print(f'Status: {resp.status_code}')
if resp.status_code == 201:
    dl = resp.json().get('browser_download_url', '')
    print(f'Download URL: {dl}')
else:
    print(resp.text[:500])
