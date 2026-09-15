#!/usr/bin/env python3
"""
QA final automatizado de Landing Page.
Cobre só o que se verifica com número. Julgamento (anti-IA, anti-generico,
claims, autocritica) continua sendo do agente — ver skill lp-qa.

  lp_qa.py <url> [--out DIR]
"""
import argparse, asyncio, json, os, pathlib, re, sys
from playwright.async_api import async_playwright


def _libs_chromium() -> None:
    """Chromium headless precisa de libnss3/libnspr4, que faltam em muita imagem enxuta
    de Debian/Ubuntu (WSL incluso). Quando o sistema nao as tem, scripts/chromium-libs.sh
    deixa uma copia no repositorio; aqui ela e injetada via LD_LIBRARY_PATH antes de o
    browser subir. Nao exige root e nao altera o sistema. Com as libs instaladas, este
    caminho extra e inofensivo."""
    aqui = pathlib.Path(__file__).resolve()
    candidatos = [aqui.parent / "runtime" / "lib"]
    if len(aqui.parents) > 3:
        candidatos.append(aqui.parents[3] / "shared" / "runtime" / "lib")
    candidatos.append(pathlib.Path.home() / ".claude" / "art-builder" / "runtime" / "lib")
    for d in candidatos:
        if (d / "libnspr4.so").exists():
            anterior = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = f"{d}:{anterior}" if anterior else str(d)
            return


_libs_chromium()

VIEWS = [('mobile', 390, 844), ('tablet', 820, 1180), ('desktop', 1440, 900)]

CONTRASTE = r"""
()=>{const lum=c=>{const s=c.map(v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)});return .2126*s[0]+.7152*s[1]+.0722*s[2]};
const parse=s=>{const m=s.match(/rgba?\(([^)]+)\)/);if(!m)return null;const p=m[1].split(',').map(parseFloat);return{c:p.slice(0,3),a:p.length>3?p[3]:1}};
const bg=el=>{let n=el;while(n&&n!==document.documentElement){const b=parse(getComputedStyle(n).backgroundColor);if(b&&b.a>.5)return b.c;n=n.parentElement}return[255,255,255]};
const out=[];document.querySelectorAll('p,span,a,li,h1,h2,h3,dt,dd,label,small,b,i,figcaption,button,summary').forEach(el=>{
const t=(el.innerText||'').trim();if(!t||el.children.length>0)return;const cs=getComputedStyle(el);
if(cs.visibility==='hidden'||cs.display==='none'||parseFloat(cs.opacity)<.5)return;
const r=el.getBoundingClientRect();if(r.width<2||r.height<2)return;const fg=parse(cs.color);if(!fg)return;
const b=bg(el),l1=lum(fg.c),l2=lum(b),ra=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);
const px=parseFloat(cs.fontSize),w=parseInt(cs.fontWeight)||400,big=px>=24||(px>=18.66&&w>=700);
if(ra<(big?3:4.5))out.push({txt:t.slice(0,34),cls:String(el.className).slice(0,28),ratio:+ra.toFixed(2)})});
const v=new Set();return out.filter(o=>{const k=o.cls+o.ratio;if(v.has(k))return false;v.add(k);return true})}
"""

ESTRUTURA = r"""
() => {
  const txt = document.body.innerText;
  const secs = [...document.querySelectorAll('main > section')];
  const btns = [...document.querySelectorAll('a.btn, button, .fab, a[class*=cta]')].filter(b => !b.hasAttribute('role'));
  const rot = {};
  btns.forEach(b => {
    const t = (b.innerText || '').trim().replace(/\s+/g, ' ');
    if (t) rot[t] = (rot[t] || 0) + 1;
  });
  const caps = [];
  document.querySelectorAll('p, span, div, h3').forEach(e => {
    if (e.children.length) return;
    const t = (e.innerText || '').trim();
    if (t.length < 4 || t.length > 60) return;
    const up = getComputedStyle(e).textTransform === 'uppercase';
    if (up || (t === t.toUpperCase() && /[A-ZÀ-Ú]{4}/.test(t))) caps.push(t);
  });
  const cards = document.querySelectorAll('[class*=card],[class*=pill],[class*=badge],[class*=chip]').length;
  const stop = new Set(['para','com','que','uma','dos','das','seu','sua','por','mais','como','pelo','pela','isso','este','esta','quando','onde','entao','todo','toda','muito','nao','sem','você','voce','aqui','pode','ser','tem']);
  const w = {};
  (txt.toLowerCase().match(/[a-zà-ú]{4,}/g) || []).forEach(x => { if (!stop.has(x)) w[x] = (w[x] || 0) + 1; });
  const rep = Object.entries(w).filter(p => p[1] >= 6).sort((a, b) => b[1] - a[1]).slice(0, 10);
  return {
    secoes: secs.length,
    secoes_cls: secs.map(s => (s.className || '').split(' ')[0]),
    ctas: btns.length,
    ctas_rotulos: rot,
    caixa_alta: [...new Set(caps)].slice(0, 12),
    cards_pills: cards,
    h1: document.querySelectorAll('h1').length,
    h2: document.querySelectorAll('h2').length,
    palavras_repetidas: rep,
    palavras_total: (txt.match(/\S+/g) || []).length
  };
}
"""


A11Y = r"""
()=>{
const imgs=[...document.images];
const semAlt=imgs.filter(i=>i.getAttribute('alt')===null).length;
const altVazio=imgs.filter(i=>i.getAttribute('alt')==='').length;
const semDim=imgs.filter(i=>!i.getAttribute('width')||!i.getAttribute('height')).length;
const dimErrada=imgs.filter(i=>i.naturalWidth&&i.getAttribute('width')&&Math.abs(+i.getAttribute('width')-i.naturalWidth)>2).map(i=>i.getAttribute('src'));
const lazy=imgs.filter(i=>i.loading==='lazy').length;
const campos=[...document.querySelectorAll('input,select,textarea')];
const semLabel=campos.filter(c=>!c.id||!document.querySelector(`label[for="${c.id}"]`)).length;
const focaveis=[...document.querySelectorAll('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])')].length;
const tabs=document.querySelectorAll('[role=tab]').length;
const pequenos=[...document.querySelectorAll('a,button')].filter(e=>{const r=e.getBoundingClientRect();
  return r.width>0&&r.height>0&&(r.height<40||r.width<40)}).length;
return {imgs:imgs.length, sem_alt:semAlt, alt_vazio:altVazio, sem_dimensao:semDim,
        dimensao_errada:dimErrada, lazy:lazy, campos:campos.length, campos_sem_label:semLabel,
        focaveis:focaveis, tabs:tabs, alvos_pequenos:pequenos};
}
"""

DESIGN = r"""
() => {
  const vis = el => { const c = getComputedStyle(el); const r = el.getBoundingClientRect();
    return c.display !== 'none' && c.visibility !== 'hidden' && r.width > 1 && r.height > 1; };
  const txt = [...document.querySelectorAll('h1,h2,h3,p,li,a,span,button,summary,cite,blockquote')].filter(vis);
  const px = {}, fam = {}, peso = {};
  txt.forEach(e => { const c = getComputedStyle(e);
    const t = (e.innerText || '').trim(); if (!t) return;
    px[Math.round(parseFloat(c.fontSize))] = 1;
    fam[c.fontFamily.split(',')[0].replace(/["']/g, '')] = 1;
    peso[c.fontWeight] = 1; });
  const escala = Object.keys(px).map(Number).sort((a, b) => a - b);
  const secs = [...document.querySelectorAll('main > section')].map(s => Math.round(s.getBoundingClientRect().height));
  const media = secs.reduce((a, b) => a + b, 0) / (secs.length || 1);
  const desvio = Math.sqrt(secs.reduce((a, b) => a + (b - media) ** 2, 0) / (secs.length || 1));
  const imgs = [...document.images].filter(vis).map(i => {
    const r = i.getBoundingClientRect(); return +(r.width / r.height).toFixed(2); });
  const raios = {}; const cores = {};
  [...document.querySelectorAll('*')].filter(vis).forEach(e => { const c = getComputedStyle(e);
    if (c.borderRadius && c.borderRadius !== '0px') raios[c.borderRadius] = 1;
    const b = c.backgroundColor; if (b && b !== 'rgba(0, 0, 0, 0)') cores[b] = (cores[b] || 0) + 1; });
  const paras = [...document.querySelectorAll('p')].filter(vis).map(e => {
    const t = (e.innerText || '').trim(); const w = e.getBoundingClientRect().width;
    const cw = parseFloat(getComputedStyle(e).fontSize) * 0.5;
    return t.length > 40 ? Math.round(w / cw) : null; }).filter(Boolean);
  return {
    escala_px: escala, familias: Object.keys(fam), pesos: Object.keys(peso).sort(),
    secoes_altura: secs, ritmo_desvio: Math.round(desvio),
    ritmo_variacao: media ? +(desvio / media).toFixed(2) : 0,
    img_proporcoes: [...new Set(imgs)],
    raios: Object.keys(raios).slice(0, 8),
    cores_fundo: Object.entries(cores).sort((a, b) => b[1] - a[1]).slice(0, 6).map(x => x[0]),
    medida_texto: [...new Set(paras)].sort((a, b) => a - b)
  };
}
"""


async def rodar(url, out):
    os.makedirs(out, exist_ok=True)
    rel = {'url': url}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for nome, w, h in VIEWS:
            pg = await b.new_page(viewport={'width': w, 'height': h})
            erros, falhas = [], []
            pg.on('pageerror', lambda e: erros.append(str(e)[:90]))
            pg.on('requestfailed', lambda r: falhas.append(r.url.split('/')[-1][:40]))
            await pg.goto(url, wait_until='load')
            await pg.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager')")
            await pg.wait_for_timeout(2200)
            v = {}
            v['altura'] = await pg.evaluate("document.body.scrollHeight")
            v['overflow_x'] = await pg.evaluate("document.documentElement.scrollWidth>document.documentElement.clientWidth")
            v['imgs_quebradas'] = await pg.evaluate("[...document.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>i.getAttribute('src'))")
            v['erros_js'] = erros[:5]; v['requisicoes_falhas'] = falhas[:5]
            if nome == 'desktop':
                rel['estrutura'] = await pg.evaluate(ESTRUTURA)
                rel['a11y'] = await pg.evaluate(A11Y)
                rel['contraste'] = await pg.evaluate(CONTRASTE)
                rel['design'] = await pg.evaluate(DESIGN)
                # teclado nas tabs, se houver
                if rel['a11y']['tabs']:
                    await pg.focus('[role=tab]')
                    antes = await pg.evaluate("document.querySelectorAll('[role=tabpanel]:not([hidden])')[0]?.id")
                    await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(250)
                    depois = await pg.evaluate("document.querySelectorAll('[role=tabpanel]:not([hidden])')[0]?.id")
                    rel['teclado_tabs'] = 'ok' if antes != depois else 'NAO RESPONDE'
                # formulario: valida sem simular envio
                if await pg.query_selector('form'):
                    btn = await pg.query_selector('form button[type=submit]')
                    if btn:
                        await btn.click(); await pg.wait_for_timeout(400)
                        rel['form_validacao'] = await pg.evaluate(
                            "document.querySelectorAll('.bad,[aria-invalid=true],:invalid').length")
            # capturas para o agente olhar
            await pg.screenshot(path=os.path.join(out, f'{nome}_dobra.png'))
            rel[nome] = v
            await pg.close()
        await b.close()
    return rel


def imprimir(r):
    e, a = r.get('estrutura', {}), r.get('a11y', {})
    P = lambda s: print(s)
    P('=' * 60); P(f"QA · {r['url']}"); P('=' * 60)
    P('\n— COMPACTAÇÃO —')
    n = e.get('secoes', 0)
    P(f"  seções principais: {n}  {'OK' if 3 <= n <= 5 else 'FORA DA META (3-5)'}   {e.get('secoes_cls')}")
    P(f"  palavras no corpo: {e.get('palavras_total')}")
    P('\n— CTA —')
    P(f"  total de CTAs: {e.get('ctas')}")
    for t, c in sorted(e.get('ctas_rotulos', {}).items(), key=lambda x: -x[1]):
        P(f"    {c}x  “{t[:44]}”" + ('   <- repetido' if c > 1 else ''))
    P('\n— SINAIS DE IA —')
    ca = e.get('caixa_alta', [])
    P(f"  microtítulos em caixa alta: {len(ca)}  {ca[:6] if ca else ''}")
    P(f"  cards/pills/badges: {e.get('cards_pills')}")
    rep = e.get('palavras_repetidas', [])
    P(f"  palavras repetidas 6x+: {[f'{k}({v})' for k,v in rep] if rep else 'nenhuma'}")
    P('\n— ACESSIBILIDADE —')
    P(f"  imagens: {a.get('imgs')} · sem alt: {a.get('sem_alt')} · alt vazio (decorativa): {a.get('alt_vazio')}")
    P(f"  sem width/height: {a.get('sem_dimensao')} · dimensão divergente: {len(a.get('dimensao_errada',[]))}")
    P(f"  campos de formulário: {a.get('campos')} · sem label: {a.get('campos_sem_label')}")
    P(f"  alvos de toque < 40px: {a.get('alvos_pequenos')}")
    if 'teclado_tabs' in r: P(f"  navegação por teclado nas tabs: {r['teclado_tabs']}")
    if 'form_validacao' in r: P(f"  validação do formulário ao enviar vazio: {r['form_validacao']} campo(s) marcados")
    c = r.get('contraste', [])
    P(f"  contraste WCAG: {len(c)} problema(s)")
    for x in c[:6]: P(f"    {x['ratio']}  “{x['txt']}”  .{x['cls']}")
    P('\n— RENDER —')
    for nome, _, _ in VIEWS:
        v = r.get(nome, {})
        flags = []
        if v.get('overflow_x'): flags.append('OVERFLOW-X')
        if v.get('imgs_quebradas'): flags.append(f"{len(v['imgs_quebradas'])} IMG QUEBRADA")
        if v.get('erros_js'): flags.append('ERRO JS')
        if v.get('requisicoes_falhas'): flags.append('REQ FALHOU')
        P(f"  {nome:8s} altura={v.get('altura'):6d}px  {'· '.join(flags) if flags else 'sem problemas'}")
    d = r.get('design', {})
    if d:
        P('\n— DESIGN —')
        esc = d.get('escala_px', [])
        P(f"  escala tipográfica: {len(esc)} tamanhos  {esc}")
        P(f"  famílias: {d.get('familias')} · pesos: {d.get('pesos')}")
        sec = d.get('secoes_altura', [])
        P(f"  altura das seções: {sec}")
        rv = d.get('ritmo_variacao', 0)
        P(f"  variação de ritmo: {rv}  {'BAIXA — seções muito parecidas' if rv < 0.28 else 'ok'}")
        P(f"  proporções de imagem: {d.get('img_proporcoes')}")
        P(f"  raios de canto distintos: {d.get('raios')}")
        P(f"  cores de fundo dominantes: {d.get('cores_fundo')}")
        mt = d.get('medida_texto', [])
        ruins = [x for x in mt if x > 95]
        P(f"  medida de texto (caracteres/linha): {mt}" + ('   <- linha longa demais' if ruins else ''))
    P('\n— O QUE ESTE SCRIPT NÃO VERIFICA —')
    P('  foco na oferta, claims sustentados, prova junto da promessa, naturalidade,')
    P('  ritmo visual, teste anti-genérico e autocrítica final: olhe as capturas e decida.')


ap = argparse.ArgumentParser()
ap.add_argument('url'); ap.add_argument('--out', default='/tmp/lp-qa'); ap.add_argument('--json', action='store_true')
a = ap.parse_args()
r = asyncio.run(rodar(a.url, a.out))
if a.json: print(json.dumps(r, ensure_ascii=False, indent=1))
else:
    imprimir(r); print(f"\ncapturas em {a.out}/")
