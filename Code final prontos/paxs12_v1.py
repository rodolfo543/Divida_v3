"""PAXS12: DI + 5,40%, cláusulas 6.11 a 6.13 da escritura.

14/10/2026 é inferido do primeiro PU da Vórtx e deve ser confirmado pelo
comprovante da primeira integralização. A projeção mantém o último DI conhecido.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, getcontext
from urllib.request import urlopen
from urllib.parse import urlencode
import json

getcontext().prec = 40
D = Decimal
DATA_INICIO_RENTABILIDADE = date(2026, 10, 14)
VENCIMENTO = date(2031, 9, 30)
QUANTIDADE = D('151899')  # quantidade emitida; confirmar total integralizado
PU_INICIAL = D('1000')
TAXA_AA = D('0.054')
PU_VAZIO_E_NOMINAL = True

def arred(x, n):
    return x.quantize(D(1).scaleb(-n), rounding=ROUND_HALF_UP)

def trunc(x, n):
    return x.quantize(D(1).scaleb(-n), rounding=ROUND_DOWN)

def pascoa(y):
    a=y%19; b=y//100; c=y%100; d=b//4; e=b%4; f=(b+8)//25
    g=(b-f+1)//3; h=(19*a+b-d-g+15)%30; i=c//4; k=c%4
    l=(32+2*e+2*i-h-k)%7; m=(a+11*h+22*l)//451
    return date(y,(h+l-7*m+114)//31,(h+l-7*m+114)%31+1)

def util(d):
    p=pascoa(d.year)
    feriados={(1,1),(4,21),(5,1),(9,7),(10,12),(11,2),(11,15),(11,20),(12,25)}
    return d.weekday()<5 and (d.month,d.day) not in feriados and d not in {p-timedelta(days=48),p-timedelta(days=47),p-timedelta(days=2),p+timedelta(days=60)}

def taxas_bcb():
    # Série 4389: CDI anual, com duas casas, conforme exigido na escritura.
    taxas = {date(2026,10,d): D('13.65') for d in (14,15,16,19,20,21,22,23,26,27,28,29)}
    parametros = urlencode({'formato':'json','dataInicial':'14/10/2026','dataFinal':date.today().strftime('%d/%m/%Y')})
    try:
        with urlopen('https://api.bcb.gov.br/dados/serie/bcdata.sgs.4389/dados?'+parametros, timeout=15) as response:
            for item in json.load(response):
                taxas[datetime.strptime(item['data'],'%d/%m/%Y').date()] = D(item['valor'])
    except Exception:
        pass
    return taxas

def calcular_fluxo(taxas=None, hoje=None):
    taxas = taxas_bcb() if taxas is None else taxas
    hoje = hoje or date.today()
    if DATA_INICIO_RENTABILIDADE not in taxas:
        raise ValueError('CDI inicial ausente; cálculo interrompido.')
    data = DATA_INICIO_RENTABILIDADE
    acumulado = D(1)
    ultima_taxa = None
    dias = 0
    diarias = []
    while data <= VENCIMENTO:
        if util(data):
            fator_di = arred(acumulado, 8)
            fator_spread = arred((D(1)+TAXA_AA) ** (D(dias)/D(252)), 9)
            fator = arred(fator_di*fator_spread, 9)
            juros = trunc(PU_INICIAL*(fator-D(1)),8)
            cheio = PU_INICIAL+juros
            pagamento = data == VENCIMENTO
            diarias.append({'Data':data.strftime('%d/%m/%Y'),'Dia_Util':'SIM',
                'Tipo_Dia':'DATA_PAGAMENTO' if pagamento else 'ACUMULACAO',
                'PU_VNa_Atualizado_Dia':PU_INICIAL,'PU_Valor_Bruto':cheio,
                'PU_Juros_Acumulado':juros,'PU_Amort_Dia':PU_INICIAL if pagamento else D(0),
                'PU_Total_Pago_Dia':cheio if pagamento else D(0),
                'PU_Juros_Pago_Dia':juros if pagamento else D(0),
                'Saldo_Bruto_R$':PU_INICIAL*QUANTIDADE,
                'Saldo_Fechamento_R$':D(0) if pagamento else cheio*QUANTIDADE,
                'Fator_Juros':fator,'Projecao':data>hoje})
            if pagamento:
                break
            taxa = taxas.get(data)
            if taxa is None:
                # Data corrente pode ainda não ter sido divulgada; seu DI só afeta o dia seguinte.
                if data < hoje:
                    raise ValueError(f'DI histórico ausente em {data:%d/%m/%Y}; atualize a série 4389 do BCB.')
                taxa = ultima_taxa
            if taxa is None:
                raise ValueError('Taxa DI indisponível para projeção.')
            ultima_taxa = taxa
            tdi = arred((D(1)+taxa/D(100))**(D(1)/D(252))-D(1),8)
            acumulado = trunc(acumulado*(D(1)+tdi),16)
            dias += 1
        data += timedelta(days=1)
    fim=diarias[-1]; juros=fim['PU_Juros_Acumulado']; total=PU_INICIAL+juros
    eventos=[{'Evento':'Vencimento (projeção CDI)', 'Data_Pgto':VENCIMENTO.strftime('%d/%m/%Y'),
        'PU_VNa_Atualizado':PU_INICIAL,'PU_Juros':juros,'PU_Amort':PU_INICIAL,'PU_Total_Pago':total,
        'Juros_R$':juros*QUANTIDADE,'Amort_R$':PU_INICIAL*QUANTIDADE,'PMT_Total':total*QUANTIDADE,
        'Saldo_Devedor_R$':D(0),'Fator_Juros':fim['Fator_Juros'],'TAI_Amort':D(1)}]
    return eventos, diarias, 'CDI BCB/SGS 4389; projeção com último CDI disponível'
