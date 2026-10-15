#!/usr/bin/env python3
"""Управление сервером через API панели Pterodactyl (BubbleHosting).

Ключ берётся из переменной окружения PTERO_API_KEY (ptlc_...), в чат и файлы его не писать.
  PTERO_URL        адрес панели (по умолчанию https://panel.bubble.wtf)
  PTERO_SERVER     короткий ID сервера (если не задан — берётся единственный сервер аккаунта)

Команды:
  ptero.py servers                     список серверов
  ptero.py cmd "<команда>" [...]       отправить команды в консоль
  ptero.py power start|stop|restart|kill
  ptero.py ls <папка>
  ptero.py get <путь на сервере> [локальный файл]
  ptero.py put <локальный файл> <папка на сервере>
  ptero.py unzip <папка> <имя архива>
  ptero.py mv <папка> <откуда> <куда>   переименовать/перенести (пути относительно папки)
"""
import json
import os
import sys
import urllib.parse
import urllib.request
import uuid

URL = os.environ.get('PTERO_URL', 'https://panel.bubble.wtf').rstrip('/')


def api(method, path, body=None, raw=False):
    req = urllib.request.Request(URL + '/api/client' + path, method=method)
    req.add_header('Authorization', 'Bearer ' + os.environ['PTERO_API_KEY'])
    req.add_header('Accept', 'application/json')
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, data, timeout=120) as r:
        out = r.read()
    if raw:
        return out
    return json.loads(out) if out else None


def server_id():
    sid = os.environ.get('PTERO_SERVER')
    if sid:
        return sid
    servers = api('GET', '')['data']
    if len(servers) != 1:
        sys.exit('серверов несколько, задайте PTERO_SERVER: ' +
                 ', '.join(s['attributes']['identifier'] for s in servers))
    return servers[0]['attributes']['identifier']


def upload(sid, local, directory):
    target = api('GET', f'/servers/{sid}/files/upload')['attributes']['url']
    target += '&directory=' + urllib.parse.quote(directory)
    boundary = uuid.uuid4().hex
    name = os.path.basename(local)
    with open(local, 'rb') as f:
        content = f.read()
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{name}"\r\n'
            'Content-Type: application/octet-stream\r\n\r\n').encode() + content + f'\r\n--{boundary}--\r\n'.encode()
    req = urllib.request.Request(target, data=body, method='POST')
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    urllib.request.urlopen(req, timeout=600).read()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    op, args = sys.argv[1], sys.argv[2:]
    if op == 'servers':
        for s in api('GET', '')['data']:
            a = s['attributes']
            print(a['identifier'], a['name'])
        return
    sid = server_id()
    q = urllib.parse.quote
    if op == 'cmd':
        for c in args:
            api('POST', f'/servers/{sid}/command', {'command': c})
            print('>', c)
    elif op == 'power':
        api('POST', f'/servers/{sid}/power', {'signal': args[0]})
        print('power', args[0])
    elif op == 'ls':
        for f in api('GET', f'/servers/{sid}/files/list?directory={q(args[0])}')['data']:
            a = f['attributes']
            print(('d ' if not a['is_file'] else 'f ') + a['name'], a['size'])
    elif op == 'get':
        data = api('GET', f'/servers/{sid}/files/contents?file={q(args[0])}', raw=True)
        if len(args) > 1:
            open(args[1], 'wb').write(data)
        else:
            sys.stdout.write(data.decode('utf-8', 'replace'))
    elif op == 'put':
        upload(sid, args[0], args[1])
        print('загружено', args[0], '->', args[1])
    elif op == 'unzip':
        api('POST', f'/servers/{sid}/files/decompress', {'root': args[0], 'file': args[1]})
        print('распаковано', args[1])
    elif op == 'mv':
        api('PUT', f'/servers/{sid}/files/rename', {'root': args[0], 'files': [{'from': args[1], 'to': args[2]}]})
        print('перенесено', args[1], '->', args[2])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
