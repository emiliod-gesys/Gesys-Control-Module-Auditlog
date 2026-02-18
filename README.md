# Gesys Control Users – Odoo Apps

Módulo **Control - User Activity Audit** para Odoo. Una rama por versión mayor de Odoo, según [lineamientos de Odoo Apps](https://apps.odoo.com/apps/upload).

| Rama    | Odoo |
|--------|------|
| `17.0` | 17   |
| `18.0` | 18   |
| `19.0` | 19   |

## Publicar en Odoo Apps Store

1. **Crea el repositorio en tu cuenta** (GitHub o GitLab):
   - Crea un repo vacío, por ejemplo: `gesys-control-users` (o el nombre que prefieras).
   - No inicialices con README si vas a hacer push de este repo.

2. **Añade el remoto y sube las ramas** (en esta carpeta):
   ```bash
   git remote add origin ssh://git@github.com/TU_USUARIO/gesys-control-users.git
   # o GitLab: ssh://git@gitlab.com/TU_USUARIO/gesys-control-users.git
   git push -u origin 17.0
   git push origin 18.0
   git push origin 19.0
   ```

3. **Registra el repo en Odoo Apps**:
   - Entra en [Submit your Apps & Themes](https://apps.odoo.com/apps/upload) e inicia sesión.
   - Usa la URL en formato SSH, por ejemplo:
     - GitHub: `ssh://git@github.com/TU_USUARIO/gesys-control-users#17.0` (y las ramas 18.0, 19.0 se detectan).
   - Repos privados: autoriza al usuario **online-odoo** (GitHub) o **OdooApps (apps@odoo.com)** (GitLab) para lectura.

4. **Requisitos para la tienda** (revisar en cada módulo):
   - Icono PNG en `static/description/icon.png`.
   - Opcional: `'images': ['images/main_screenshot.png']` en el manifest y capturas en la carpeta `images/`.
   - Descripción en `static/description/index.html` (ya incluida).

## Estructura por rama

En cada rama solo está el módulo correspondiente a esa versión de Odoo:

- **17.0** → `gesys_control_users_v17/`
- **18.0** → `gesys_control_users_v18/`
- **19.0** → `gesys_control_users_v19/`

## Licencia

LGPL-3 (según manifest del módulo).
