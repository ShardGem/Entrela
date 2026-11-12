"""Formatação de apresentação; valores científicos originais são preservados."""
from datetime import datetime
from math import isfinite


def quantity(value, precision=6):
    if value is None:
        return '—'
    number = float(value)
    if not isfinite(number):
        return 'Indisponível'
    if number and (abs(number) < 1e-3 or abs(number) >= 1e6):
        return f'{number:.3e}'
    return f'{number:.{precision}g}'


def timestamp(value):
    try:
        date = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return date.astimezone().strftime('%d/%m/%Y %H:%M')
    except (ValueError, TypeError):
        return str(value or '—')
