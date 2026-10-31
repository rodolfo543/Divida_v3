"""Planejamento de aportes de 1/6, isolado de saldos bancários e dos motores de dívida."""
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def shift_month(month, offset):
    year, number = map(int, month.split('-'))
    result = year * 12 + number - 1 + offset
    return f'{result // 12:04d}-{result % 12 + 1:02d}'


def cents(value):
    return int((Decimal(str(value)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def amount(value):
    return format(Decimal(value) / 100, '.2f')


def split_six(value):
    """Arredonda acumulados proporcionais: seis parcelas não negativas fecham a PMT."""
    total = cents(value)
    checkpoints = [int((Decimal(total) * i / 6).quantize(Decimal('1'), rounding=ROUND_HALF_UP)) for i in range(7)]
    return [amount(checkpoints[i + 1] - checkpoints[i]) for i in range(6)]


def build_recomposition(root=ROOT):
    content = (root / 'data/calendar.json').read_bytes()
    calendar = json.loads(content)
    rules = {r['code']: r for r in json.loads((root / 'recomposition_rules.json').read_text(encoding='utf-8'))}
    catalog = {r['code']: r for r in json.loads((root / 'vortx_catalog.json').read_text(encoding='utf-8'))}
    instruments, contributions = [], []
    for instrument in calendar['instruments']:
        rule = rules[instrument['code']]
        entry = {**instrument, **rule, 'cycles': [], 'review': catalog[instrument['code']].get('review', '')}
        if rule['eligible']:
            # O contrato vincula o início à primeira AMORTIZAÇÃO, não aos juros de carência.
            targets = [e for e in calendar['events'] if e['code'] == rule['code'] and cents(e['amortization']) > 0 and cents(e['payment']) > 0]
            if rule['end'] == 'penultimate':
                targets = targets[:-1]
            occupied = set()
            for target in targets:
                month = target['date'][:7]
                parts = split_six(target['payment'])
                cycle = {'id': target['id'], 'payment_date': target['date'], 'payment': target['payment'],
                         'interest': target['interest'], 'amortization': target['amortization'],
                         'start_month': shift_month(month, -6), 'end_month': shift_month(month, -1),
                         'one_sixth': amount(int((Decimal(cents(target['payment'])) / 6).quantize(Decimal('1'), rounding=ROUND_HALF_UP))),
                         'installments': []}
                cumulative = 0
                for i, value in enumerate(parts):
                    competence = shift_month(month, i - 6)
                    if competence in occupied:
                        raise ValueError(f"Ciclos sobrepostos: {rule['code']} / {competence}")
                    occupied.add(competence)
                    cumulative += cents(value)
                    row = {'month': competence, 'amount': value, 'installment': i + 1, 'planned_cumulative': amount(cumulative)}
                    cycle['installments'].append(row)
                    contributions.append({**row, 'code': rule['code'], 'operation': instrument['operation'],
                                          'label': instrument['label'], 'series': instrument['series'],
                                          'payment_date': target['date'], 'payment': target['payment'],
                                          'cycle_id': target['id'], 'rank': rule['rank'], 'pending': instrument['pending']})
                entry['cycles'].append(cycle)
            entry['start_month'] = entry['cycles'][0]['start_month'] if entry['cycles'] else None
            entry['end_month'] = entry['cycles'][-1]['end_month'] if entry['cycles'] else None
        instruments.append(entry)
    result = {'schema_version': 1, 'generated_at': calendar['generated_at'], 'local_as_of': calendar['local_as_of'],
              'calendar_sha256': hashlib.sha256(content).hexdigest(), 'instruments': instruments,
              'contributions': sorted(contributions, key=lambda r: (r['month'], r['code']))}
    for directory in (root / 'data', root / 'docs/data'):
        (directory / 'recomposition.json').write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f"Recomposição: {sum(i['eligible'] for i in instruments)} instrumentos aplicáveis; {len(contributions)} aportes programados.")
    return result


if __name__ == '__main__':
    build_recomposition()
