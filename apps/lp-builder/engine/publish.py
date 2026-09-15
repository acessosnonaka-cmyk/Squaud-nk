#!/usr/bin/env python3
"""
Publicação de preview de Landing Pages do LP Builder.

  publish <slug> <dir>     valida, versiona, publica e testa HTTP
  rollback <slug> [--to V] volta para a versão anterior (ou uma específica)
  ls [slug]                lista clientes e versões
  serve [--port 8090]      sobe o servidor local que serve todos os previews

Raiz de publicação: ~/.claude/lp-builder/previews/<slug>/
    current -> versions/<carimbo>/     (troca atômica)
    versions/<carimbo>/                (histórico para rollback)

Destino remoto (VPS) é opcional e vem de publish.conf.json. Sem ele, publica local.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

HOME = os.path.expanduser('~/.claude/lp-builder')
ROOT = os.path.join(HOME, 'previews')          # única raiz onde se pode escrever
CONF = os.path.join(HOME, 'publish.conf.json')
SLUG = re.compile(r'^[a-z0-9][a-z0-9-]{1,40}$')
MANTER = 8                                      # versões preservadas por cliente


def conf():
    if os.path.exists(CONF):
        return json.load(open(CONF, encoding='utf-8'))
    c = {'base_url': 'http://localhost:8090', 'remote': None}
    os.makedirs(HOME, exist_ok=True)
    json.dump(c, open(CONF, 'w', encoding='utf-8'), indent=2)
    return c


def slug_ok(s):
    if not SLUG.match(s):
        sys.exit(f"ERRO: slug inválido '{s}'. Use a-z, 0-9 e hífen (2 a 41 chars).")
    return s


def dentro_da_raiz(p):
    """Trava de segurança: nenhum caminho fora de ROOT pode ser tocado."""
    real = os.path.realpath(p)
    if not (real == os.path.realpath(ROOT) or real.startswith(os.path.realpath(ROOT) + os.sep)):
        sys.exit(f"ERRO: caminho fora da raiz de publicação: {real}")
    return real


def hash_dir(d):
    h = hashlib.sha1()
    for base, _, fs in sorted(os.walk(d)):
        for f in sorted(fs):
            p = os.path.join(base, f)
            h.update(os.path.relpath(p, d).encode())
            with open(p, 'rb') as fh:
                for b in iter(lambda: fh.read(65536), b''):
                    h.update(b)
    return h.hexdigest()[:12]


def cmd_publish(a):
    s = slug_ok(a.slug)
    src = os.path.realpath(os.path.expanduser(a.dir))
    t0 = time.time()

    # 1 · validação
    if not os.path.isdir(src):
        sys.exit(f"ERRO: diretório não existe: {src}")
    if not os.path.isfile(os.path.join(src, 'index.html')):
        sys.exit(f"ERRO: {src} não contém index.html")
    n = sum(len(f) for _, _, f in os.walk(src))
    peso = sum(os.path.getsize(os.path.join(b, f)) for b, _, fs in os.walk(src) for f in fs)
    print(f"validação · {n} arquivos · {peso//1024} KB · hash={hash_dir(src)}")

    cli = dentro_da_raiz(os.path.join(ROOT, s))
    vers = os.path.join(cli, 'versions')
    os.makedirs(vers, exist_ok=True)
    carimbo = time.strftime('%Y%m%d-%H%M%S')
    dest = dentro_da_raiz(os.path.join(vers, carimbo))

    # 2 · versão anterior fica intacta (é o backup)
    ant = os.path.realpath(os.path.join(cli, 'current')) if os.path.islink(os.path.join(cli, 'current')) else None
    if ant:
        print(f"versão anterior preservada: {os.path.basename(ant)}")

    # 3 · cópia
    shutil.copytree(src, dest)
    # 4 · permissões previsíveis
    for b, ds, fs in os.walk(dest):
        for d in ds: os.chmod(os.path.join(b, d), 0o755)
        for f in fs: os.chmod(os.path.join(b, f), 0o644)
    os.chmod(dest, 0o755)

    # 5 · troca atômica do ponteiro
    tmp = os.path.join(cli, '.current.novo')
    if os.path.islink(tmp) or os.path.exists(tmp):
        os.remove(dentro_da_raiz(tmp))
    os.symlink(os.path.join('versions', carimbo), tmp)
    os.replace(tmp, os.path.join(cli, 'current'))

    # 6 · poda do histórico (só dentro da raiz, só diretórios de versão)
    todas = sorted(d for d in os.listdir(vers) if re.match(r'^\d{8}-\d{6}$', d))
    for velha in todas[:-MANTER]:
        shutil.rmtree(dentro_da_raiz(os.path.join(vers, velha)))
        print(f"  podada versão antiga {velha}")

    c = conf()
    url = c['base_url'].rstrip('/') + '/' + s + '/'

    # 7 · envio ao VPS, se configurado
    r = c.get('remote')
    if r:
        alvo = f"{r['user']}@{r['host']}:{r['path'].rstrip('/')}/{s}/"
        cmd = ['rsync', '-az', '--delete']
        if r.get('key'):
            cmd += ['-e', f"ssh -i {os.path.expanduser(r['key'])} -o StrictHostKeyChecking=accept-new"]
        cmd += [dest.rstrip('/') + '/', alvo]
        print('enviando ao VPS…')
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode:
            sys.exit(f"ERRO no rsync: {p.stderr.strip()[:300]}")
        url = r.get('base_url', c['base_url']).rstrip('/') + '/' + s + '/'

    # 8 · teste HTTP
    st = teste(url)
    print(f"publicado em {time.time()-t0:.1f}s")
    print(f"HTTP {st}  ->  {url}")
    if st != 200:
        sys.exit("ERRO: preview não respondeu 200. Verifique se o servidor está no ar (`publish.py serve`).")


def teste(url, tent=3):
    for i in range(tent):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                return r.status
        except Exception as e:
            code = getattr(e, 'code', None)
            if code:
                return code
            time.sleep(1.5)
    return 0


def cmd_rollback(a):
    s = slug_ok(a.slug)
    cli = dentro_da_raiz(os.path.join(ROOT, s))
    vers = os.path.join(cli, 'versions')
    todas = sorted(d for d in os.listdir(vers) if re.match(r'^\d{8}-\d{6}$', d))
    if len(todas) < 2 and not a.to:
        sys.exit('ERRO: não há versão anterior para voltar.')
    atual = os.path.basename(os.path.realpath(os.path.join(cli, 'current')))
    alvo = a.to or todas[todas.index(atual) - 1]
    if alvo not in todas:
        sys.exit(f"ERRO: versão '{alvo}' não existe. Disponíveis: {', '.join(todas)}")
    tmp = os.path.join(cli, '.current.novo')
    if os.path.islink(tmp): os.remove(dentro_da_raiz(tmp))
    os.symlink(os.path.join('versions', alvo), tmp)
    os.replace(tmp, os.path.join(cli, 'current'))
    c = conf()
    url = (c.get('remote') or c)['base_url'].rstrip('/') + '/' + s + '/'
    print(f"rollback: {atual} -> {alvo}\nHTTP {teste(url)}  ->  {url}")


def cmd_ls(a):
    if not os.path.isdir(ROOT):
        print('nenhum preview publicado'); return
    c = conf(); base = (c.get('remote') or c)['base_url'].rstrip('/')
    for s in sorted(os.listdir(ROOT)):
        if a.slug and s != a.slug: continue
        cli = os.path.join(ROOT, s); vers = os.path.join(cli, 'versions')
        if not os.path.isdir(vers): continue
        todas = sorted(d for d in os.listdir(vers) if re.match(r'^\d{8}-\d{6}$', d))
        atual = os.path.basename(os.path.realpath(os.path.join(cli, 'current'))) if os.path.islink(os.path.join(cli, 'current')) else '—'
        print(f"{s:20s} {base}/{s}/   versões={len(todas)}  atual={atual}")
        if a.slug:
            for v in todas:
                print(f"    {'*' if v == atual else ' '} {v}")


def cmd_serve(a):
    """Serve todos os previews em /<slug>/ a partir de current/."""
    import http.server, socketserver, posixpath, urllib.parse

    class H(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path):
            path = urllib.parse.urlparse(path).path
            parts = [p for p in posixpath.normpath(urllib.parse.unquote(path)).split('/') if p not in ('', '.', '..')]
            if not parts:
                return os.path.join(ROOT, '__index__')
            slug, resto = parts[0], parts[1:]
            if not SLUG.match(slug):
                return os.path.join(ROOT, '__nao_existe__')
            base = os.path.join(ROOT, slug, 'current')
            alvo = os.path.realpath(os.path.join(base, *resto)) if resto else os.path.join(base, 'index.html')
            if not os.path.realpath(alvo).startswith(os.path.realpath(ROOT)):
                return os.path.join(ROOT, '__nao_existe__')
            if os.path.isdir(alvo):
                alvo = os.path.join(alvo, 'index.html')
            return alvo

        def do_GET(self):
            if self.path == '/':
                cs = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d))) if os.path.isdir(ROOT) else []
                body = ('<meta charset=utf-8><title>Previews</title>'
                        '<body style="font:15px system-ui;padding:40px"><h1>Previews</h1><ul>' +
                        ''.join(f'<li><a href="/{c}/">{c}</a></li>' for c in cs) + '</ul>').encode()
                self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body); return
            return super().do_GET()

        def log_message(self, *args): pass

    # Threading: o navegador abre a LP com ~10 requisicoes em paralelo (css, js, fontes,
    # imagens). Um TCPServer serial derruba parte delas e a pagina chega quebrada.
    class S(socketserver.ThreadingTCPServer):
        daemon_threads = True
        allow_reuse_address = True

    with S(('0.0.0.0', a.port), H) as s:
        print(f'servindo previews em http://localhost:{a.port}/  (Ctrl+C para parar)')
        s.serve_forever()


p = argparse.ArgumentParser(description='Publicação de preview de LPs')
sub = p.add_subparsers(dest='cmd', required=True)
x = sub.add_parser('publish');  x.add_argument('slug'); x.add_argument('dir'); x.set_defaults(fn=cmd_publish)
x = sub.add_parser('rollback'); x.add_argument('slug'); x.add_argument('--to'); x.set_defaults(fn=cmd_rollback)
x = sub.add_parser('ls');       x.add_argument('slug', nargs='?'); x.set_defaults(fn=cmd_ls)
x = sub.add_parser('serve');    x.add_argument('--port', type=int, default=8090); x.set_defaults(fn=cmd_serve)
a = p.parse_args(); a.fn(a)
