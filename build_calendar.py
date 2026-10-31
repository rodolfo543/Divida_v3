"""Agenda de leitura dos cronogramas publicados, sem recalcular ou mover eventos."""
import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent
D = Decimal


def money(value):
    return format(D(str(value or 0)).quantize(D('.01'), rounding=ROUND_HALF_UP), '.2f')


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFD', str(text or '')) if not unicodedata.combining(c)).upper()


def iso_date(text):
    return datetime.strptime(text, '%d/%m/%Y').date().isoformat()


def first(raw, *keys):
    return next((raw[key] for key in keys if raw.get(key) not in (None, '')), None)


def calendar_event(row, instrument, quantity, sequence):
    raw = row.get('raw') or {}
    payment, interest, amortization = (D(str(row.get(k) or 0)) for k in ('payment', 'interest', 'amortization'))
    incorporation = first(raw, 'Juros_Capitalizado_R$', 'Juros_Incorporado_R$')
    if incorporation is None:
        pu = first(raw, 'PU_Juros_Incorporado', 'PU_Juros_Capitalizado', 'PU_Juros_Capitalizado_Dia', 'Juros_Capitalizado')
        incorporation = D(str(pu or 0)) * quantity
    incorporation = D(str(incorporation))
    kind = normalized(row.get('label')) + normalized(raw.get('Evento'))
    if incorporation == 0 and payment == 0 and ('INCORPOR' in kind or 'CAPITAL' in kind):
        incorporation = D(str(row.get('pu_juros') or 0)) * quantity
    if payment == 0 and incorporation == 0:
        return None
    maturity = payment > 0 and amortization > 0 and D(str(row.get('balance') or 0)) == 0
    event_type = 'maturity' if maturity else 'payment' if payment > 0 else 'incorporation'
    title = ('Vencimento' if maturity else 'PMT · juros e amortização' if amortization > 0 and interest > 0 else
             'PMT · amortização' if amortization > 0 else 'PMT · juros') if payment > 0 else 'Incorporação de juros'
    extra = first(raw, 'Amort_Extraordinaria_R$', 'Amortizacao_Extraordinaria_R$')
    if extra is None:
        extra = D(str(first(raw, 'PU_Amort_Extraordinaria', 'Amortizacao_Extraordinaria', 'PU_Amex_Dia') or 0)) * quantity
    extra = D(str(extra))
    event_date = iso_date(row['date'])
    reference = first(raw, 'Data_Ref')
    return {
        'id': f"{instrument['code']}-{event_date}-{sequence}", 'date': event_date,
        'operation': instrument['operation'], 'company': instrument['label'],
        'code': instrument['code'], 'series': instrument['series'], 'type': event_type, 'title': title,
        'payment': money(payment), 'interest': money(interest), 'amortization': money(amortization),
        'extra': money(extra), 'ordinary': money(amortization - extra), 'incorporation': money(incorporation),
        'pu_full': str(row.get('pu_cheio')) if row.get('pu_cheio') is not None else None,
        'pu_payment': str(row.get('pu_total')) if row.get('pu_total') is not None else None,
        'reference_date': iso_date(reference) if reference else None,
        'pending': instrument.get('pending', False), 'note': instrument.get('review') if instrument.get('pending') else '',
    }


def build_calendar(root=ROOT):
    manifest = json.loads((root / 'data/operations.json').read_text(encoding='utf-8'))
    catalog = json.loads((root / 'vortx_catalog.json').read_text(encoding='utf-8'))
    sources, events, instruments = {}, [], []
    for instrument in catalog:
        op = instrument['operation']
        if op not in sources:
            content = (root / 'data/operations' / f'{op}.json').read_bytes()
            sources[op] = (json.loads(content, parse_float=D), hashlib.sha256(content).hexdigest())
        payload, digest = sources[op]
        view = payload['variants'][instrument['variant']] if instrument['variant'] else payload
        fields = {field['label']: field['value'] for field in view['operation']['overview_fields']}
        quantity = D(str(fields['Quantidade emitida']))
        rows = view.get('table_series', view.get('series', []))
        instruments.append({k: instrument[k] for k in ('code', 'operation', 'label', 'series')} |
                           {'source_sha256': digest, 'quantity': str(quantity), 'pending': instrument.get('pending', False)})
        for sequence, row in enumerate(rows):
            event = calendar_event(row, instrument, quantity, sequence)
            if event:
                events.append(event)
    events.sort(key=lambda e: (e['date'], e['company'], e['code'], e['id']))
    result = {'schema_version': 1, 'generated_at': manifest['generated_at'],
              'local_as_of': manifest['generated_at_iso'][:10],
              'built_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'instruments': instruments, 'events': events}
    content = json.dumps(result, ensure_ascii=False, separators=(',', ':'))
    for parent in (root / 'data', root / 'docs/data'):
        parent.mkdir(parents=True, exist_ok=True)
        (parent / 'calendar.json').write_text(content, encoding='utf-8')
    print(f"Calendário: {len(events)} eventos em {len(instruments)} instrumentos; sem linhas consolidadas duplicadas.")
    return result


if __name__ == '__main__':
    build_calendar()
