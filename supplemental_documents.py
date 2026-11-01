"""Documentos identificados por origem; não altera os motores financeiros."""
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent


def valid_href(item):
    href = item.get('href', '')
    if item.get('source_type') == 'axs_ri':
        u = urlparse(href)
        return (u.scheme == 'https' and u.hostname == 'apiri.axsenergia.com.br'
                and not u.username and not u.password and u.port in (None, 443)
                and u.path.startswith('/storage/v1/object/public/documentos/'))
    return (item.get('source_type') == 'axs_archive'
            and bool(re.fullmatch(r'\./assets/documents/[a-z0-9-]+\.pdf', href)))


def supplemental_for(code, root=ROOT):
    path = root / 'documents-supplemental.json'
    if not path.exists():
        return []
    records = json.loads(path.read_text(encoding='utf-8'))
    result = []
    for item in records:
        if code not in item.get('codes', []):
            continue
        if (not re.fullmatch(r'axs-[a-z0-9-]+', item.get('id', ''))
                or not re.fullmatch(r'[a-f0-9]{64}', item.get('sha256', ''))
                or not valid_href(item)):
            raise ValueError(f'Documento complementar inválido: {item.get("id")}')
        result.append({k: v for k, v in item.items() if k != 'codes'} | {'code': code})
    return result


def sync_assets(root=ROOT):
    path = root / 'documents-supplemental.json'
    if not path.exists():
        return
    for item in json.loads(path.read_text(encoding='utf-8')):
        if not valid_href(item):
            raise ValueError(f'Origem inválida: {item.get("id")}')
        if item['source_type'] != 'axs_archive':
            continue
        relative = item['href'][2:]
        source = root / relative
        if hashlib.sha256(source.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'Arquivo difere da cópia conferida: {relative}')
        target = root / 'docs' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
