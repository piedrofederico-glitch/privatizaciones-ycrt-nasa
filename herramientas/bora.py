#!/usr/bin/env python3
"""Escáner de la primera y la segunda sección del Boletín Oficial (boletinoficial.gob.ar). Solo biblioteca estándar.

Uso:
  bora.py escanear --empresa DIR_EMPRESA [--empresa OTRA ...] --salida DIR [--fecha AAAAMMDD] [--dias N]
  bora.py aviso ID AAAAMMDD [--salida DIR]      # texto de un aviso (y PDF con --salida)

`escanear` lee el sumario de cada fecha, abre una sola vez el texto completo de cada aviso y lo
compara contra las expresiones regulares `terminos_bora` del config.json de cada empresa. Para cada
aviso que coincide y no figura en el estado.json de esa empresa baja el texto (.txt) y el PDF
oficial a <salida>/<empresa>/bora/, lo marca como visto y deja el detalle en
<salida>/<empresa>/bora.json. Imprime un resumen por empresa.
Si el BORA no responde, la sección del día se lee del PDF completo que el BORA publica en el CDN de
ARSAT (texto oficial; solo la edición del día; sin anexos web); cada coincidencia lleva el recorte de
páginas como PDF. Si ARSAT también falla, la primera sección se revisa en BOA (boa.com.ar): solo la edición
del día, con resúmenes en lugar del texto completo y sin PDF; esas coincidencias llevan 'fuente': 'BOA'
y 'pdf_url'. Los avisos de BOA sin coincidencia no se marcan, para revisarlos con el texto completo
cuando el BORA vuelva (por eso conviene --dias 1 en la corrida siguiente).
La segunda sección (sociedades: edictos de asambleas, reformas de estatuto, aumentos de capital,
directorios) trae cientos de avisos por día: de esa sección solo se abren los avisos cuyo renglón
del sumario (razón social) coincide con los términos; en el estado se guardan como "s2:<id>". --dias N revisa también los N días anteriores
(útil los lunes o después de una corrida fallida).
"""
import argparse, datetime, html, json, os, re, subprocess, sys, tempfile, time, urllib.request

BASE = 'https://www.boletinoficial.gob.ar'
op = urllib.request.build_opener()
op.addheaders = [('User-Agent', 'Mozilla/5.0')]


def log(*a):
    print(*a, file=sys.stderr)


def get(url, raw=False, intentos=4):
    for i in range(intentos):
        try:
            b = op.open(BASE + url, timeout=90).read()
            return b if raw else b.decode('utf-8', 'ignore')
        except Exception as e:
            if i == intentos - 1:
                raise
            log(f'[reintento {i + 1}] {url}: {e}')
            time.sleep(2 ** (i + 1))


def limpio(h):
    h = re.sub(r'(?s)<script.*?</script>|<style.*?</style>', ' ', h)
    h = re.sub(r'(?i)<br\s*/?>|</(p|div|tr|li|h\d)>', '\n', h)
    h = html.unescape(re.sub(r'<[^>]+>', ' ', h))
    return '\n'.join(re.sub(r'[ \t\xa0]+', ' ', l).strip() for l in h.splitlines() if l.strip())


def sumario(fecha, seccion='primera'):
    """[(id, organismo, norma, codigo)] de esa sección y fecha."""
    t = get(f'/seccion/{seccion}/{fecha}')
    out = []
    for m in re.finditer(rf'<a href="/detalleAviso/{seccion}/(\d+)/(\d{{8}})"[^>]*>(.*?)</a>', t, re.S):
        if m.group(2) != fecha:
            continue
        ps = [limpio(p) for p in re.findall(r'(?s)<p[^>]*>(.*?)</p>', m.group(3))]
        out.append((m.group(1), *(ps + ['', '', ''])[:3]))
    return list(dict((o[0], o) for o in out).values())


def aviso(id_, fecha, seccion='primera'):
    t = get(f'/detalleAviso/{seccion}/{id_}/{fecha}')
    i = t.find('id="tituloDetalleAviso"'); j = t.find('id="cuerpoDetalleAviso"')
    titulo = limpio(t[t.find('>', i) + 1:t.rfind('<', 0, j)]) if 0 < i < j else ''
    cuerpo = limpio(t[t.find('>', j) + 1:j + 400000]) if j > 0 else ''
    cuerpo = cuerpo[:cuerpo.find('Fecha de publicación')] if 'Fecha de publicación' in cuerpo else cuerpo
    return titulo, cuerpo


def sumario_boa(fecha):
    """Respaldo de la primera sección cuando el BORA no responde: https://boa.com.ar/ (resumen privado del BORA).
    Solo publica la edición del día (sin archivo ni segunda sección) y trae un resumen hecho con IA, no el texto.
    Devuelve [(id, organismo, norma, codigo, resumen)] si la edición publicada es la de `fecha`."""
    r = urllib.request.urlopen(urllib.request.Request('https://boa.com.ar/', headers={'User-Agent': 'Mozilla/5.0'}), timeout=90)
    t = r.read().decode('utf-8', 'ignore')
    out = []
    for bloque in re.split(r'<div class="item[ "]', t)[1:]:
        m = re.search(r'detalleAviso/primera/(\d+)/(\d{8})', bloque)
        if not m or m.group(2) != fecha:
            continue
        campo = lambda c: limpio((re.search(rf'(?s)<div class="{c}">(.*?)</div>', bloque) or [None, ''])[1])
        out.append((m.group(1), campo('entity'), campo('norm'), campo('code'), campo('summary').replace('Resumen:', '').strip()))
    if not out:
        raise RuntimeError(f'BOA no tiene la edición del {fecha} (solo publica la del día)')
    return list(dict((o[0], o) for o in out).values())


ARSAT = 'https://s3.arsat.com.ar/cdn-bo-001/pdf-del-dia/{}.pdf'
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
         'noviembre', 'diciembre']
ENCABEZADO = re.compile(r'^(BOLET[IÍ]N OFICIAL N[º°].*|\d{1,3}|(Lunes|Martes|Mi[eé]rcoles|Jueves|Viernes|S[aá]bado|Domingo) \d{1,2} de \w+ de \d{4})$')


def avisos_pdf(fecha, seccion, trabajo):
    """Respaldo con texto oficial: PDF completo de la sección del día en el CDN de ARSAT (lo publica el BORA).
    Solo existe la edición del día (se pisa al día siguiente) y no trae los anexos que se publican solo en la web.
    Devuelve (ruta_pdf, [aviso]) con aviso = {marca, edicto, titulo, texto, pag_ini, pag_fin}."""
    os.makedirs(trabajo, exist_ok=True)
    ruta = os.path.join(trabajo, f'{fecha}_{seccion}.pdf')
    if not os.path.exists(ruta):
        r = urllib.request.urlopen(urllib.request.Request(ARSAT.format(seccion), headers={'User-Agent': 'Mozilla/5.0'}), timeout=180)
        b = r.read()
        if b[:4] != b'%PDF':
            raise RuntimeError('ARSAT no devolvió un PDF')
        open(ruta, 'wb').write(b)
    t = subprocess.run(['pdftotext', ruta, '-'], capture_output=True, text=True, check=True).stdout
    d = datetime.datetime.strptime(fecha, '%Y%m%d').date()
    if f'{d.day} de {MESES[d.month - 1]} de {d.year}' not in t[:3000]:
        os.remove(ruta)
        raise RuntimeError(f'el PDF de ARSAT no es la edición del {fecha} (solo publica la del día)')
    out, fin_ant = [], 0
    for m in re.finditer(r'#I(\d+)I#(.*?)#F\1F#', t, re.S):
        previo = [l.strip() for l in t[fin_ant:m.start()].replace('\f', '\n').splitlines()]
        previo = [l for l in previo if l and not ENCABEZADO.match(l)]
        cuerpo = m.group(2).replace('\f', '\n')
        ed = re.search(r'e\.\s*\d{2}/\d{2}/\d{4}\s*N[°º]\s*(\d+/\d+)', cuerpo)
        titulo = ' / '.join(previo[-2:]) if seccion == 'segunda' else ' / '.join(previo[-3:])
        out.append({'marca': m.group(1), 'edicto': ed.group(1) if ed else m.group(1), 'titulo': titulo,
                    'texto': '\n'.join(previo[-3:]) + '\n' + cuerpo.strip(),
                    'pag_ini': t.count('\f', 0, m.start()) + 1, 'pag_fin': t.count('\f', 0, m.end()) + 1})
        fin_ant = m.end()
    if not out:
        raise RuntimeError('no se pudieron separar los avisos del PDF de ARSAT')
    return ruta, out


def recortar_pdf(ruta, ini, fin, destino):
    """Copia las páginas ini..fin del PDF completo (el aviso puede compartir página con otros)."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['pdfseparate', '-f', str(ini), '-l', str(fin), ruta, os.path.join(tmp, 'p%d.pdf')], check=True)
        subprocess.run(['pdfunite', *[os.path.join(tmp, f'p{i}.pdf') for i in range(ini, fin + 1)], destino], check=True)
    return destino


def url_aviso(id_, fecha, seccion='primera'):
    return f'{BASE}/detalleAviso/{seccion}/{id_}/{fecha}'


def escanear(empresas, salida, fecha, dias):
    """Escanea una vez el BORA y compara cada aviso con los términos de cada empresa.
    `salida` recibe una subcarpeta por empresa (<salida>/<empresa>/bora)."""
    limite = (datetime.date.today() - datetime.timedelta(days=20)).strftime('%Y%m%d')
    emp = {}
    for e in empresas:
        cfg = json.load(open(os.path.join(e, 'config.json')))
        pe = os.path.join(e, 'estado.json')
        est = json.load(open(pe)) if os.path.exists(pe) else {}
        est.setdefault('bora', {}).setdefault('vistos', {})
        rev = est['bora'].setdefault('revisados', {})  # leídos sin coincidencias, por fecha (20 días)
        for f in [f for f in rev if f < limite]:
            del rev[f]
        nombre_e = os.path.basename(os.path.normpath(e))
        emp[nombre_e] = {'ruta': pe, 'est': est, 'pats': [re.compile(p, re.I) for p in cfg['terminos_bora']],
                         'salida': os.path.join(salida, nombre_e, 'bora'),
                         'res': {'coincidencias': [], 'fechas_revisadas': [], 'errores': []}}
    base = datetime.datetime.strptime(fecha, '%Y%m%d').date()
    # si hubo días sin BORA oficial (caído o solo BOA), se retrocede hasta el último leído (máximo 7)
    ultimas = [x['est']['bora'].get('ultima_ok') for x in emp.values()]
    if all(ultimas):
        atraso = (base - datetime.datetime.strptime(min(ultimas), '%Y%m%d').date()).days
        dias = max(dias, min(atraso, 7))
    for d in range(dias, -1, -1):
        f = (base - datetime.timedelta(days=d)).strftime('%Y%m%d')
        for seccion in ('primera', 'segunda'):
            fuente, motivo = 'BORA', ''
            if all(seccion in x['est']['bora'].get('leido_pdf', {}).get(f, []) for x in emp.values()):
                for x in emp.values():
                    x['res']['fechas_revisadas'].append(f'{f} {seccion} (ya leída completa en el PDF de ARSAT)')
                continue
            try:
                items = sumario(f, seccion)
            except Exception as ex:
                motivo = f'BORA sin respuesta ({ex})'
                try:
                    ruta_pdf, items = avisos_pdf(f, seccion, os.path.join(salida, '_arsat')); fuente = 'ARSAT'
                except Exception as ex2:
                    motivo += f'; ARSAT: {ex2}'
                    if seccion == 'segunda':
                        for x in emp.values():
                            x['res']['errores'].append(f'segunda {f}: {motivo}. BOA no publica la segunda sección: buscar edictos por la web')
                        continue
                    try:
                        items = sumario_boa(f); fuente = 'BOA'
                    except Exception as ex3:
                        for x in emp.values():
                            x['res']['errores'].append(f'primera {f}: {motivo}; BOA: {ex3}')
                        continue
                for x in emp.values():
                    x['res']['errores'].append(f'{seccion} {f}: {motivo}; revisada en {fuente}' +
                                               (' (texto oficial del PDF del día, sin anexos web)' if fuente == 'ARSAT'
                                                else ' (resúmenes, sin texto oficial ni PDF)'))
            for x in emp.values():
                x['res']['fechas_revisadas'].append(f'{f} {seccion} ({len(items)} avisos, {fuente})')
                if fuente in ('BORA', 'ARSAT') and seccion == 'primera' and f > x['est']['bora'].get('ultima_ok', ''):
                    x['est']['bora']['ultima_ok'] = f
                if fuente == 'ARSAT':
                    lp = x['est']['bora'].setdefault('leido_pdf', {})
                    lp.setdefault(f, []).append(seccion)
                    for g in [g for g in lp if g < limite]:
                        del lp[g]
            if fuente == 'ARSAT':
                for a in items:
                    clave = f"e:{a['edicto']}"
                    nombre = re.sub(r'[^\w.\-]+', '_', f"{f}_{seccion}_{a['edicto']}_{a['titulo']}")[:100]
                    recorte = None
                    for k, x in emp.items():
                        b = x['est']['bora']
                        if clave in b['vistos']:
                            continue
                        donde = a['titulo'] if seccion == 'segunda' else a['texto']  # segunda: solo la razón social
                        hits = sorted({m.group(0) for p in x['pats'] for m in p.finditer(donde)})
                        if not hits:
                            continue
                        os.makedirs(x['salida'], exist_ok=True)
                        open(os.path.join(x['salida'], nombre + '.txt'), 'w').write(
                            f"Fuente: PDF del día de la {seccion} sección (ARSAT), páginas {a['pag_ini']}-{a['pag_fin']}\n\n{a['texto']}")
                        pdf = None
                        try:
                            if recorte is None:
                                recorte = recortar_pdf(ruta_pdf, a['pag_ini'], a['pag_fin'],
                                                       os.path.join(salida, '_arsat', nombre + '.pdf'))
                            pdf = os.path.join(x['salida'], nombre + '.pdf'); open(pdf, 'wb').write(open(recorte, 'rb').read())
                        except Exception as ex:
                            x['res']['errores'].append(f"recorte PDF {a['edicto']}: {ex}")
                        b['vistos'][clave] = f
                        x['res']['coincidencias'].append({'id': a['edicto'], 'seccion': seccion, 'fecha': f, 'organismo': a['titulo'],
                                                          'norma': '', 'codigo': f"edicto N° {a['edicto']}", 'terminos': hits,
                                                          'fuente': 'ARSAT', 'url': f'{BASE}/seccion/{seccion}/{f}',
                                                          'texto': os.path.join(x['salida'], nombre + '.txt'), 'pdf': pdf,
                                                          'anexos': 'los anexos que se publican solo en la web no están en el PDF del día'})
                continue
            if fuente == 'BOA':
                for id_, org, norma, cod, resumen in items:
                    texto = f'{org}\n{norma}\n{cod}\nResumen de BOA (no es el texto oficial): {resumen}'
                    nombre = re.sub(r'[^\w.\-]+', '_', f'{f}_primera_{id_}_{norma or org}')[:100]
                    for k, x in emp.items():
                        b = x['est']['bora']
                        if id_ in b['vistos'] or id_ in b['revisados'].get(f, []):
                            continue
                        hits = sorted({m.group(0) for p in x['pats'] for m in p.finditer(texto)})
                        if not hits:
                            continue  # sin marcar: cuando vuelva el BORA se revisa con el texto completo
                        os.makedirs(x['salida'], exist_ok=True)
                        open(os.path.join(x['salida'], nombre + '.txt'), 'w').write(f'{url_aviso(id_, f)}\n\n{texto}')
                        b['vistos'][id_] = f
                        x['res']['coincidencias'].append({'id': id_, 'seccion': 'primera', 'fecha': f, 'organismo': org,
                                                          'norma': norma, 'codigo': cod, 'terminos': hits, 'fuente': 'BOA',
                                                          'url': url_aviso(id_, f), 'texto': os.path.join(x['salida'], nombre + '.txt'),
                                                          'pdf': None, 'pdf_url': f'{BASE}/pdf/aviso/primera/{id_}/{f}', 'anexos': ''})
                continue
            for id_, org, norma, cod in items:
                clave = id_ if seccion == 'primera' else f's2:{id_}'
                renglon = f'{org}\n{norma}\n{cod}'
                pend = {k: x for k, x in emp.items()
                        if clave not in x['est']['bora']['vistos'] and clave not in x['est']['bora']['revisados'].get(f, [])}
                if seccion == 'segunda':  # solo los edictos cuya razón social coincide
                    pend = {k: x for k, x in pend.items() if any(p.search(renglon) for p in x['pats'])}
                if not pend:
                    continue
                try:
                    titulo, cuerpo = aviso(id_, f, seccion)
                except Exception as ex:
                    for x in pend.values():
                        x['res']['errores'].append(f'aviso {seccion} {id_}: {ex}')
                    continue
                texto = f'{renglon}\n{titulo}\n{cuerpo}'
                nombre = re.sub(r'[^\w.\-]+', '_', f'{f}_{seccion}_{id_}_{norma or org}')[:100]
                pdf_b = None
                for k, x in pend.items():
                    hits = sorted({m.group(0) for p in x['pats'] for m in p.finditer(texto)})
                    if not hits:
                        x['est']['bora']['revisados'].setdefault(f, []).append(clave)
                        continue
                    os.makedirs(x['salida'], exist_ok=True)
                    open(os.path.join(x['salida'], nombre + '.txt'), 'w').write(f'{url_aviso(id_, f, seccion)}\n\n{texto}')
                    pdf = None
                    try:
                        if pdf_b is None:
                            pdf_b = get(f'/pdf/aviso/{seccion}/{id_}/{f}', raw=True)
                        if pdf_b[:4] == b'%PDF':
                            pdf = os.path.join(x['salida'], nombre + '.pdf'); open(pdf, 'wb').write(pdf_b)
                    except Exception as ex:
                        x['res']['errores'].append(f'pdf {seccion} {id_}: {ex}')
                    x['est']['bora']['vistos'][clave] = f
                    x['res']['coincidencias'].append({'id': id_, 'seccion': seccion, 'fecha': f, 'organismo': org,
                                                      'norma': norma, 'codigo': cod, 'terminos': hits,
                                                      'url': url_aviso(id_, f, seccion),
                                                      'texto': os.path.join(x['salida'], nombre + '.txt'), 'pdf': pdf,
                                                      'anexos': 'tiene anexos: abrirlos desde la url' if 'Ver anexos' in cuerpo else ''})
    for k, x in emp.items():
        json.dump(x['est'], open(x['ruta'], 'w'), ensure_ascii=False, indent=1, sort_keys=True)
        os.makedirs(os.path.join(salida, k), exist_ok=True)
        json.dump(x['res'], open(os.path.join(salida, k, 'bora.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({k: {'coincidencias': len(x['res']['coincidencias']), 'errores': x['res']['errores'],
                          'archivo': os.path.join(salida, k, 'bora.json')} for k, x in emp.items()}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    es = sp.add_parser('escanear'); es.add_argument('--empresa', action='append', required=True)
    es.add_argument('--salida', required=True)
    es.add_argument('--fecha', default=datetime.date.today().strftime('%Y%m%d')); es.add_argument('--dias', type=int, default=0)
    av = sp.add_parser('aviso'); av.add_argument('id'); av.add_argument('fecha'); av.add_argument('--salida')
    av.add_argument('--seccion', default='primera', choices=['primera', 'segunda'])
    a = ap.parse_args()
    if a.cmd == 'escanear':
        escanear(a.empresa, a.salida, a.fecha, a.dias)
    else:
        titulo, cuerpo = aviso(a.id, a.fecha, a.seccion)
        print(f'{url_aviso(a.id, a.fecha, a.seccion)}\n{titulo}\n\n{cuerpo}')
        if a.salida:
            os.makedirs(a.salida, exist_ok=True)
            open(os.path.join(a.salida, f'{a.fecha}_{a.id}.pdf'), 'wb').write(get(f'/pdf/aviso/{a.seccion}/{a.id}/{a.fecha}', raw=True))
