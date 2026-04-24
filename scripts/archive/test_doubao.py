# -*- coding: utf-8 -*-
import json, urllib.request, urllib.error

keys = [
    'your-doubao-api-key-uuid',
    'api-key-xxxxxxxx-your-doubao-api-key-uuid',
]

for api_key in keys:
    print(f'Trying key: {api_key[:40]}...')
    payload = json.dumps({
        'model': 'doubao-seed-2-0-lite-260215',
        'messages': [{'role': 'user', 'content': 'say hi'}],
        'max_tokens': 50
    }).encode('utf-8')
    
    req = urllib.request.Request(
        'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
        data=payload,
        headers={
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': f'Bearer {api_key}'
        },
        method='POST'
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        text = result['choices'][0]['message']['content']
        print(f'  OK! Response: {text[:100]}')
        break
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:300]
        print(f'  FAIL {e.code}: {body}')
    except Exception as e:
        print(f'  ERROR: {type(e).__name__}: {e}')
