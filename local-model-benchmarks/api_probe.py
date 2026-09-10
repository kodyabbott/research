"""One local chat request, run as a killable child for the thinking probe deadline."""
import json
import re
import sys
import time
import urllib.request

if __name__ == '__main__':
    arguments = json.load(sys.stdin)
    url = arguments['url']
    if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]+/api/chat', url):
        raise ValueError('Probe only accepts a local Ollama chat URL')
    request = urllib.request.Request(url, data=json.dumps(arguments['body']).encode(),
                                    headers={'Content-Type': 'application/json'})
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=arguments['seconds']) as response:
        raw = response.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError('Probe response exceeded 16 MiB')
    result = json.loads(raw)
    result['clientWallMs'] = round((time.monotonic() - started) * 1000, 1)
    print(json.dumps(result))
