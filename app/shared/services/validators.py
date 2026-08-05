import re
def validator_names(v: str | None) -> str | None:
    if v is None:
        return v
    v = v.strip()
    if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚüÜñÑ\s'-]+$", v):
        raise ValueError('Solo se permiten letras, espacios, guiones y apóstrofes')
    return v 

def validator_username(v: str | None) -> str | None:
    if v is None:
        return v
    v=v.strip().lower()
    if not re.match(r'^[a-z0-9_-]+$', v):
        raise ValueError('El username solo puede contener letras minúsculas, números, guiones (-) y guiones bajos (_)')
    
    if v[0] in '-_' or v[-1] in '-_':
        raise ValueError('El username no puede empezar ni terminar con guión (-) o guión bajo (_)')
    
    if '--' in v or '__' in v or '-_' in v or '_-' in v:
        raise ValueError('El username no puede tener guiones o guiones bajos consecutivos')

    return v

def validator_password(v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not re.search(r'\d', v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v

def validator_phone(v: str | None) -> str | None:
    if v is None:
        return v
    if not re.match(r'^\+\d{5,15}$', v):
        raise ValueError('El número de teléfono debe tener entre 5 y 15 dígitos y comenzar con +')
    return v



def validator_business_name(v: str | None) -> str | None:
    if v is None:
        return v
    v = v.strip()
    if not re.match(r"^[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s&'.-]+$", v):
        raise ValueError("Solo se permiten letras, números, espacios y caracteres comunes de empresas (&, -, ., ').")
    return v

def validator_currency(v: str) -> str:
    """Normaliza el código de moneda al formato ISO de tres letras."""
    v = v.strip().upper()
    if not re.match(r"^[A-Z]{3}$",v):
        raise ValueError("La moneda debe ser un código de tres letras, por ejemplo BOB o USD.")
    return v

def validator_product_name(value: str) -> str:
    value = value.strip()

    if not re.fullmatch(
        r"[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s&'./#_-]+",
        value,
    ):
        raise ValueError(
            "El nombre del producto contiene caracteres no válidos."
        )

    return value