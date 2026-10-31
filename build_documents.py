"""Catálogo de documentos públicos da Vórtx. Não publica arquivos locais."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
BASE = 'https://apis.vortx.com.br/vxsite/api/operacao'


def public_documents(groups, code):
    if not isinstance(groups, list):
        raise ValueError('Lista de documentos inválida')
    result = {}
    for group in groups:
        for doc in group.get('documents', []):
            url = urlparse(doc.get('url', ''))
            if doc.get('public') is not True or url.scheme != 'https' or not (url.hostname or '').endswith('.vortx.com.br'):
                continue
            key = str(doc['id'])
            if not key.isdigit():
                continue
            result[key] = {'id': key, 'name': doc.get('description') or f'Documento {key}',
                           'category': doc.get('type') or group.get('type') or 'Outros documentos',
                           'type_id': doc.get('typeId'), 'uploaded_at': doc.get('uploadTimestamp'),
                           'source_operation_id': doc.get('operationId'), 'code': code}
    return list(result.values())


def collect(config, previous=None, fetch=None):
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    documents, errors = {}, []
    for route in (0, 1):
        try:
            url = f"{BASE}/{config['operation_id']}/documentos-por-tipo/{route}"
            if fetch:
                raw = fetch(url)
            else:
                request = Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
                with urlopen(request, timeout=25) as response:
                    raw = json.load(response)
            for doc in public_documents(raw, config['code']):
                documents[doc['id']] = doc
        except Exception as error:
            errors.append(f'Consulta {route}: {error}')
    # Coleta parcial nunca apaga documentos do retrato anterior.
    if errors:
        for doc in (previous or {}).get('documents', []):
            documents.setdefault(doc['id'], doc)
    return {**config, 'documents': sorted(documents.values(), key=lambda d: (d['category'], d['name'])),
            'collected_at': now if not errors else (previous or {}).get('collected_at'),
            'attempted_at': now, 'errors': errors, 'cached': bool(errors)}


def build_documents(root=ROOT):
    catalog = json.loads((root / 'vortx_catalog.json').read_text(encoding='utf-8'))
    path = root / 'data/documents.json'
    old = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    previous = {i['code']: i for i in old.get('instruments', [])}
    configs = []
    for i in catalog:
        snap = json.loads((root / 'data/vortx/instruments' / f"{i['code']}.json").read_text(encoding='utf-8'))
        issue = snap.get('reference', {}).get('terms', {}).get('issue')
        kind = 'CRI' if i['code'][0].isdigit() else 'Debênture'
        configs.append({key: i[key] for key in ('code', 'operation_id', 'operation', 'label', 'series')} |
                       {'title': f"{kind} · {str(issue) + 'ª emissão · ' if issue else ''}{i['series']}"})
    with ThreadPoolExecutor(max_workers=3) as pool:
        instruments = list(pool.map(lambda c: collect(c, previous.get(c['code'])), configs))
    result = {'schema_version': 1, 'built_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'instruments': instruments}
    for directory in (root / 'data', root / 'docs/data'):
        (directory / 'documents.json').write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f"Documentação: {len({d['id'] for i in instruments for d in i['documents']})} documentos públicos; {len(instruments)} instrumentos.")
    return result


if __name__ == '__main__':
    build_documents()
