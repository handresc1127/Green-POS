"""Green-POS - Filtros Jinja2
Filtros personalizados para templates.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def format_currency_co(value):
    """Formatea número al formato monetario colombiano (sin centavos).
    
    Args:
        value: Número a formatear
    
    Returns:
        str: Valor formateado (ej: $1.234.567)
    """
    try:
        integer_value = int(round(float(value or 0)))
    except (ValueError, TypeError):
        integer_value = 0
    formatted = f"{integer_value:,}".replace(',', '.')
    return f"${formatted}"


def format_tz(dt, tz="America/Bogota", fmt="%d/%m/%Y, %H:%M", assume="UTC"):
    """Convierte y formatea datetime a zona horaria específica.
    
    Args:
        dt: datetime (aware o naive)
        tz: Zona horaria destino (default: America/Bogota)
        fmt: Formato strftime (default: %d/%m/%Y, %H:%M)
        assume: Zona para datetime naive (default: UTC)
    
    Returns:
        str: Fecha formateada en zona horaria destino
    """
    if dt is None:
        return ""
    
    if isinstance(tz, str):
        tz = ZoneInfo(tz)
    
    if dt.tzinfo is None:
        src = ZoneInfo(assume) if assume and assume != "UTC" else timezone.utc
        dt = dt.replace(tzinfo=src)
    
    return dt.astimezone(tz).strftime(fmt)


def format_tz_co(dt, tz="America/Bogota", assume="UTC"):
    """Formatea datetime al estilo colombiano con AM/PM en español.
    Formato: DD/MM/YYYY, H:MM a. m./p. m. (sin ceros iniciales en hora)
    
    Args:
        dt: datetime (aware o naive)
        tz: Zona horaria destino (default: America/Bogota)
        assume: Zona para datetime naive (default: UTC)
    
    Returns:
        str: Fecha y hora formateada estilo colombiano
    """
    if dt is None:
        return ""
    
    if isinstance(tz, str):
        tz = ZoneInfo(tz)
    
    if dt.tzinfo is None:
        src = ZoneInfo(assume) if assume and assume != "UTC" else timezone.utc
        dt = dt.replace(tzinfo=src)
    
    local_dt = dt.astimezone(tz)
    hour = int(local_dt.strftime('%I'))
    minute = local_dt.strftime('%M')
    period = local_dt.strftime('%p').replace('AM', 'a. m.').replace('PM', 'p. m.')
    date_str = local_dt.strftime('%d/%m/%Y')
    
    return f"{date_str}, {hour}:{minute} {period}"


def format_time_co(dt, tz="America/Bogota", assume="UTC"):
    """Formatea solo la hora al estilo colombiano: H:MM a. m./p. m.
    
    Args:
        dt: datetime (aware o naive)
        tz: Zona horaria destino (default: America/Bogota)
        assume: Zona para datetime naive (default: UTC)
    
    Returns:
        str: Hora formateada estilo colombiano
    """
    if dt is None:
        return ""
    
    if isinstance(tz, str):
        tz = ZoneInfo(tz)
    
    if dt.tzinfo is None:
        src = ZoneInfo(assume) if assume and assume != "UTC" else timezone.utc
        dt = dt.replace(tzinfo=src)
    
    local_dt = dt.astimezone(tz)
    hour = int(local_dt.strftime('%I'))
    minute = local_dt.strftime('%M')
    period = local_dt.strftime('%p').replace('AM', 'a. m.').replace('PM', 'p. m.')
    
    return f"{hour}:{minute} {period}"


def format_date_co(dt, tz="America/Bogota", assume="UTC"):
    """Formatea solo la fecha al estilo colombiano: DD/MM/YYYY
    
    Args:
        dt: datetime (aware o naive)
        tz: Zona horaria destino (default: America/Bogota)
        assume: Zona para datetime naive (default: UTC)
    
    Returns:
        str: Fecha formateada estilo colombiano
    """
    if dt is None:
        return ""
    
    if isinstance(tz, str):
        tz = ZoneInfo(tz)
    
    if dt.tzinfo is None:
        src = ZoneInfo(assume) if assume and assume != "UTC" else timezone.utc
        dt = dt.replace(tzinfo=src)
    
    local_dt = dt.astimezone(tz)
    return local_dt.strftime('%d/%m/%Y')


def register_filters(app):
    """Registra todos los filtros Jinja2 en la aplicación.
    
    Args:
        app: Instancia de Flask
    """
    app.jinja_env.filters['currency_co'] = format_currency_co
    app.jinja_env.filters['format_tz'] = format_tz
    app.jinja_env.filters['format_tz_co'] = format_tz_co
    app.jinja_env.filters['format_time_co'] = format_time_co
    app.jinja_env.filters['format_date_co'] = format_date_co
