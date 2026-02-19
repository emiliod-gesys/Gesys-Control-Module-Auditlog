# Fix: AttributeError al cerrar POS - 'bool' object has no attribute 'strftime'

## Problema

Al cerrar un punto de venta (POS), se produce:

```
AttributeError: 'bool' object has no attribute 'strftime'
File ".../account/models/account_bank_statement_line.py", line 295, in _compute_internal_index
    st_line.internal_index = f'{st_line.date.strftime("%Y%m%d")}' ...
```

Ocurre cuando `st_line.date` es `False` durante la creación de `account.move.line` en el cierre de sesión POS (método `_create_cash_statement_lines_and_cash_move_lines`).

## Solución aplicada

Se sobreescribe `_compute_internal_index` en `account.bank.statement.line` para validar que `date` sea un objeto fecha antes de llamar a `strftime`. Si es `False` o no tiene `strftime`, se usa la fecha actual como fallback.

## Aplicar en v17 y v18

**En la rama 17.0 o 18.0:**

1. Crear `gesys_control_users_vXX/models/account_bank_statement_line.py` con el mismo contenido que en v19.
2. En `models/__init__.py`, añadir al inicio:
   ```python
   from . import account_bank_statement_line
   ```

El código es compatible con Odoo 17, 18 y 19.

## Dependencias

El módulo ya depende de `account`, no se requieren cambios en el manifest.
