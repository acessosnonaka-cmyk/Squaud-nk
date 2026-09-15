#!/usr/bin/env python3
"""
Triagem progressiva de materiais no Google Drive para o LP Builder.

Subcomandos
  map     enumera pastas (contagens/tipos) — sem baixar arquivos
  rank    cruza nomes de pasta com o briefing -> ALTA / MEDIA / BAIXA
  triage  baixa thumbnails só das pastas priorizadas -> contact sheets
  fetch   baixa alta resolução apenas da shortlist

Cache por cliente em ~/.claude/lp-builder/clients/<slug>/index.json
Isolamento: cada cliente tem seu diretório; nada é compartilhado entre slugs.
"""
import argparse, hashlib, html, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.expanduser('~/.claude/lp-builder/clients')
UA = {'User-Agent': 'Mozilla/5.0 Chrome/126.0 Safari/537.36'}
IMG = re.compile(r'\.(jpe?g|png|webp|heic|avif)$', re.I)
VID = re.compile(r'\.(mp4|mov|m4v|webm)$', re.I)
TTL = 7 * 24 * 3600  # reaproveita índice por 7 dias


def slugdir(slug):
    d = os.path.join(BASE, re.sub(r'[^a-z0-9_-]+', '-', slug.lower()))
    os.makedirs(d, exist_ok=True)
    return d


def load(slug):
    p = os.path.join(slugdir(slug), 'index.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {'folders': {}, 'shortlist': []}


def save(slug, ix):
    json.dump(ix, open(os.path.join(slugdir(slug), 'index.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)


def get(url, timeout=45):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def folder_ids_from_doc(doc_url):
    """Extrai IDs de pasta + rótulo de um Google Doc público."""
    m = re.search(r'/document/d/([A-Za-z0-9_-]+)', doc_url)
    if not m:
        return []
    txt = get(f'https://docs.google.com/document/d/{m.group(1)}/export?format=txt').decode('utf-8-sig', 'ignore')
    out, seen = [], set()
    blocos = re.split(r'\[\d{2}:\d{2}[^\]]*\][^:]*:', txt)
    for b in blocos:
        fid = re.search(r'drive\.google\.com/drive/folders/([A-Za-z0-9_-]+)', b)
        if not fid or fid.group(1) in seen:
            continue
        seen.add(fid.group(1))
        rot = re.sub(r'https?://\S+', '', b).strip().replace('\n', ' ')
        out.append({'id': fid.group(1), 'label': re.sub(r'\s+', ' ', rot)[:60] or fid.group(1)})
    return out


def fingerprint(itens):
    """Assinatura barata do conteudo de uma pasta: ids + nomes ordenados."""
    h = hashlib.sha1()
    for i, n in sorted(itens):
        h.update((i + '\x1f' + n + '\x1e').encode('utf-8'))
    return h.hexdigest()[:16]


def enum_folder(fid):
    """Enumera uma pasta pública via embeddedfolderview (1 request, sem baixar arquivos)."""
    d = get(f'https://drive.google.com/embeddedfolderview?id={fid}#list').decode('utf-8', 'ignore')
    ids = re.findall(r'<div class="flip-entry" id="entry-([A-Za-z0-9_-]{20,60})"', d)
    nms = [html.unescape(x) for x in re.findall(r'flip-entry-title">([^<]+)<', d)]
    return list(zip(ids, nms))


def cmd_map(a):
    ix = load(a.client)
    alvos = folder_ids_from_doc(a.doc) if a.doc else [{'id': i, 'label': i} for i in a.folder]
    t0 = time.time()
    stat = {'nova': 0, 'inalterada': 0, 'atualizada': 0, 'ttl': 0, 'erro': 0}

    def checar(f):
        prev = ix['folders'].get(f['id'])
        try:
            itens = enum_folder(f['id'])
        except Exception as e:
            # sem rede/endpoint: cai no TTL como fallback
            if prev and (time.time() - prev.get('ts', 0)) < TTL:
                return f, None, 'ttl'
            print(f"  ! {f['label']}: {str(e)[:50]}", file=sys.stderr)
            return f, None, 'erro'
        fp = fingerprint(itens)
        if prev and prev.get('fp') == fp and not a.refresh:
            return f, None, 'inalterada'
        return f, (itens, fp), 'atualizada' if prev else 'nova'

    with ThreadPoolExecutor(max_workers=12) as ex:
        for f, dados, tipo in ex.map(checar, alvos):
            stat[tipo] += 1
            if not dados:
                continue
            itens, fp = dados
            imgs = [[i, n] for i, n in itens if IMG.search(n)]
            vids = [[i, n] for i, n in itens if VID.search(n)]
            ant = ix['folders'].get(f['id'], {})
            ix['folders'][f['id']] = {'label': f['label'], 'total': len(itens), 'n_img': len(imgs),
                                      'n_vid': len(vids), 'imgs': imgs, 'ts': time.time(), 'fp': fp,
                                      'score': ant.get('score'), 'tier': ant.get('tier')}
    save(a.client, ix)
    tot = sum(v['n_img'] for v in ix['folders'].values())
    print(f"MAPA · pastas={len(ix['folders'])} · novas={stat['nova']} inalteradas={stat['inalterada']} "
          f"atualizadas={stat['atualizada']} ttl={stat['ttl']} erro={stat['erro']} · "
          f"imagens={tot} tempo={time.time()-t0:.1f}s")
    for fid, v in sorted(ix['folders'].items(), key=lambda x: -x[1]['n_img']):
        print(f"  {v['label'][:34]:36s} img={v['n_img']:5d} vid={v['n_vid']:3d}")


def cmd_rank(a):
    ix = load(a.client)
    alta = [w.lower() for w in a.alta.split(',') if w.strip()]
    media = [w.lower() for w in (a.media or '').split(',') if w.strip()]
    ruido = [w.lower() for w in (a.ruido or '').split(',') if w.strip()]
    for fid, v in ix['folders'].items():
        nome = v['label'].lower()
        s = 0
        s += 3 * sum(1 for k in alta if k in nome)
        s += 1 * sum(1 for k in media if k in nome)
        s -= 3 * sum(1 for k in ruido if k in nome)
        if v['n_img'] == 0:
            s -= 5
        # pasta gigantesca costuma ser despejo bruto, não curadoria
        if v['n_img'] > 400:
            s -= 1
        v['score'] = s
        v['tier'] = 'ALTA' if s >= 3 else ('MEDIA' if s >= 1 else 'BAIXA')
    save(a.client, ix)
    for t in ('ALTA', 'MEDIA', 'BAIXA'):
        g = [v for v in ix['folders'].values() if v['tier'] == t]
        print(f"{t} · {len(g)} pastas · {sum(x['n_img'] for x in g)} imagens")
        for v in sorted(g, key=lambda x: -x['score'])[:12]:
            print(f"    {v['label'][:34]:36s} score={v['score']:+d} img={v['n_img']}")


def cmd_triage(a):
    ix = load(a.client)
    d = slugdir(a.client); th = os.path.join(d, 'thumbs'); os.makedirs(th, exist_ok=True)
    tiers = a.tier.upper().split(',')
    sel = [(fid, v) for fid, v in ix['folders'].items() if v.get('tier') in tiers]
    sel.sort(key=lambda x: -x[1]['score'])
    if not sel:
        print('nenhuma pasta nesse tier — rode rank antes'); return
    por = max(4, a.budget // max(1, len(sel)))
    jobs, t0 = [], time.time()
    for fid, v in sel:
        imgs = v['imgs']
        step = max(1, len(imgs) // por)
        for i, (iid, nm) in enumerate(imgs[::step][:por]):
            safe = re.sub(r'\W+', '_', v['label'])[:24]
            jobs.append((iid, os.path.join(th, f'{safe}__{i:02d}__{iid}.jpg')))

    def grab(j):
        iid, p = j
        if os.path.exists(p) and os.path.getsize(p) > 2000:
            return 2  # cache
        try:
            b = get(f'https://drive.google.com/thumbnail?id={iid}&sz=w400', 35)
            if len(b) > 2000:
                open(p, 'wb').write(b); return 1
        except Exception:
            pass
        return 0
    with ThreadPoolExecutor(max_workers=12) as ex:
        r = list(ex.map(grab, jobs))
    novos, cache = r.count(1), r.count(2)
    print(f"TRIAGEM · pastas={len(sel)} thumbs={novos+cache} (novos={novos}, cache={cache}) "
          f"falhas={r.count(0)} tempo={time.time()-t0:.1f}s")
    print(f"  thumbs em {th}")
    montar(th, os.path.join(d, 'sheet.jpg'))


def montar(th, out):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print('  (PIL ausente: contact sheet não gerado)'); return
    fs = sorted(f for f in os.listdir(th) if f.endswith('.jpg'))
    if not fs:
        return
    C, COLS = 250, 8
    rows = (len(fs) + COLS - 1) // COLS
    im = Image.new('RGB', (COLS * C, rows * (C + 30)), '#e6e6e6')
    d = ImageDraw.Draw(im)
    for i, f in enumerate(fs):
        try:
            t = Image.open(os.path.join(th, f)).convert('RGB')
        except Exception:
            continue
        t.thumbnail((C, C))
        x, y = (i % COLS) * C, (i // COLS) * (C + 30)
        im.paste(t, (x + (C - t.width) // 2, y + 24))
        d.text((x + 3, y + 4), f'[{i}] ' + f.split('__')[0][:24], fill='black')
        d.text((x + 3, y + 24 + C + 2), f.split('__')[2][:14], fill='#555')
    im.save(out, quality=84)
    print(f"  contact sheet: {out}  ({len(fs)} imagens, {rows} linhas)")



# ---------------- filtro visual sobre thumbnails (sem custo de rede) --------------
LIM = {'vazia': 12.0, 'desfoque': 22.0, 'escura': 45.0, 'estourada': 215.0,
       'chapada': 22.0, 'dup_hamming': 5}


def metricas(p):
    from PIL import Image, ImageStat, ImageFilter
    im = Image.open(p).convert('RGB'); im.thumbnail((256, 256))
    g = im.convert('L')
    e = ImageStat.Stat(g.filter(ImageFilter.FIND_EDGES))
    sg = ImageStat.Stat(g)
    sat = ImageStat.Stat(im.convert('HSV').split()[1])
    # dHash 8x8 para duplicata perceptual
    s8 = g.resize((9, 8), Image.LANCZOS).load()
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | (1 if s8[x, y] > s8[x + 1, y] else 0)
    return {'edge': e.mean[0], 'edge_sd': e.stddev[0], 'lum': sg.mean[0],
            'contr': sg.stddev[0], 'sat': sat.mean[0], 'hash': bits}


def julgar(m):
    """Rejeita apenas o que e mensuravelmente ruim. Julgamento criativo nao entra aqui."""
    if m['edge'] < LIM['vazia']:
        return 'REJEITADO', 'sem conteudo relevante (parede/vao vazio)'
    if m['edge_sd'] < LIM['desfoque']:
        return 'REJEITADO', 'desfoque forte'
    if m['lum'] < LIM['escura']:
        return 'REJEITADO', 'subexposta'
    if m['lum'] > LIM['estourada']:
        return 'REJEITADO', 'estourada'
    if m['contr'] < LIM['chapada']:
        return 'REJEITADO', 'sem contraste'
    return 'OK', ''


def cmd_screen(a):
    d = slugdir(a.client); th = os.path.join(d, 'thumbs')
    fs = sorted(f for f in os.listdir(th) if f.endswith('.jpg'))
    if not fs:
        print('sem thumbs — rode triage antes'); return
    t0 = time.time()
    res, vistos = [], []
    for i, f in enumerate(fs):
        fid = f.rsplit('__', 1)[1][:-4]
        try:
            m = metricas(os.path.join(th, f))
        except Exception as e:
            res.append((i, fid, 'REJEITADO', 'ilegivel', None)); continue
        st, why = julgar(m)
        if st == 'OK':
            for j, hh in vistos:
                if bin(m['hash'] ^ hh).count('1') <= LIM['dup_hamming']:
                    st, why = 'REJEITADO', f'quase identica a [{j}]'; break
            if st == 'OK':
                vistos.append((i, m['hash']))
        res.append((i, fid, st, why, m))
    ix = load(a.client)
    ix['rejeitados'] = [r[1] for r in res if r[2] == 'REJEITADO']
    save(a.client, ix)
    ok = [r for r in res if r[2] == 'OK']
    print(f"FILTRO · {len(fs)} candidatos · aprovados={len(ok)} rejeitados={len(res)-len(ok)} "
          f"· tempo={time.time()-t0:.1f}s")
    for i, fid, st, why, m in res:
        if st == 'REJEITADO':
            print(f"  [{i:2d}] REJEITADO — {why}")
    print("\n  Aprovados passam por SEU olho antes do fetch. O filtro nao detecta:")
    print("  obra inacabada, entulho, fios aparentes, enquadramento infeliz — isso e semantico.")
    print(f"  Revise o contact sheet: {os.path.join(d,'sheet.jpg')}")


def cmd_fetch(a):
    ix = load(a.client)
    d = slugdir(a.client); hi = os.path.join(d, 'hi'); os.makedirs(hi, exist_ok=True)
    ids = a.id
    if a.from_sheet:
        th = os.path.join(d, 'thumbs')
        fs = sorted(f for f in os.listdir(th) if f.endswith('.jpg'))
        ids = [fs[i].rsplit('__', 1)[1][:-4] for i in a.pick if i < len(fs)]
    rej = set(ix.get('rejeitados', []))
    if rej and not a.force:
        antes = len(ids)
        ids = [i for i in ids if i not in rej]
        if antes != len(ids):
            print(f"  filtro visual barrou {antes-len(ids)} candidato(s); use --force para ignorar")
    if 'rejeitados' not in ix:
        print('  aviso: rode `screen` antes do fetch para filtrar candidatos ruins')
    t0, ok = time.time(), 0
    for iid in ids:
        p = os.path.join(hi, f'{iid}.jpg')
        if os.path.exists(p) and os.path.getsize(p) > 30000:
            ok += 1; continue
        for sz in ('w2000', 'w1600'):
            try:
                b = get(f'https://drive.google.com/thumbnail?id={iid}&sz={sz}', 60)
                if len(b) > 30000:
                    open(p, 'wb').write(b); ok += 1; break
            except Exception:
                pass
    ix['shortlist'] = sorted(set(ix.get('shortlist', []) + list(ids)))
    save(a.client, ix)
    print(f"ALTA RESOLUÇÃO · {ok}/{len(ids)} em {hi} · tempo={time.time()-t0:.1f}s")


p = argparse.ArgumentParser(description='Triagem progressiva de Drive para LPs')
sub = p.add_subparsers(dest='cmd', required=True)
m = sub.add_parser('map');    m.add_argument('--client', required=True); m.add_argument('--doc'); m.add_argument('--folder', nargs='*', default=[]); m.add_argument('--refresh', action='store_true'); m.set_defaults(fn=cmd_map)
r = sub.add_parser('rank');   r.add_argument('--client', required=True); r.add_argument('--alta', required=True); r.add_argument('--media'); r.add_argument('--ruido'); r.set_defaults(fn=cmd_rank)
t = sub.add_parser('triage'); t.add_argument('--client', required=True); t.add_argument('--tier', default='ALTA'); t.add_argument('--budget', type=int, default=40); t.set_defaults(fn=cmd_triage)
sc = sub.add_parser('screen'); sc.add_argument('--client', required=True); sc.set_defaults(fn=cmd_screen)
f = sub.add_parser('fetch');  f.add_argument('--client', required=True); f.add_argument('--id', nargs='*', default=[]); f.add_argument('--from-sheet', action='store_true'); f.add_argument('--pick', nargs='*', type=int, default=[]); f.add_argument('--force', action='store_true'); f.set_defaults(fn=cmd_fetch)
a = p.parse_args(); a.fn(a)
