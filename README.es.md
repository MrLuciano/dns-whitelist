<p>
  <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (Brasil)</a> | <a href="README.fr.md">Français</a> | <b>Español</b>
</p>

# dns-whitelist

Lista de permitidos (allowlist) curada de nombres DNS consumida por **AdGuard Home**, mantenida al día por una build automatizada que obtiene catálogos publicados por los proveedores.

## Consumir

AdGuard Home → Filtros → Listas de permitidos DNS → Añadir lista de bloqueo → URL:

```
https://raw.githubusercontent.com/MrLuciano/dns-whitelist/main/whitelist.txt
```

## Qué hace

- **Obtiene catálogos en vivo de los proveedores** (catálogo de endpoints de Microsoft 365) semanalmente y mediante disparo manual; extrae los dominios que Teams y Microsoft Authenticator necesitan.
- **Carga listas YAML curadas a mano** (Google Authenticator, NetIQ, Cisco AnyConnect, Palo Alto GlobalProtect) — para servicios que no publican una allowlist legible por máquina. Consulta `sources/*.yaml` para los conjuntos de FQDNs curados y la documentación fuente que referencian.
- Valida cada candidato con reglas estrictas de sintaxis tipo RFC-1035.
- Descarta los dominios que no resuelven (no pueden estar en ninguna colisión con una blocklist si no existen, así que no pertenecen a una allowlist *dirigida*).
- Emite un `whitelist.txt` determinístico en formato de allowlist de AdGuard (`@@||dominio.com^`), con una sección por servicio.

Actualmente cubierto:

- **Microsoft Teams** — `serviceArea=Skype` en el catálogo de Microsoft 365
- **Microsoft Authenticator** — `serviceArea=Common` en el catálogo de Microsoft 365
- **Google Authenticator** — aplicación sin conexión por diseño; solo la ruta de sincronización en la nube necesita red. Curado a mano.
- **NetIQ** (Access Manager + Identity Manager) — solo los endpoints opcionales de actualización/registro/catálogo son del proveedor. Curado a mano.
- **Cisco AnyConnect / Secure Client** — dominios universales de soporte más endpoints en la nube de Umbrella y Secure Access. Curado a mano.
- **Palo Alto GlobalProtect** — solo el FQDN del portal del cliente es siempre necesario; proporcionamos los endpoints opcionales en la nube de Prisma Access / CIE / SLS. Curado a mano. **Añade el FQDN de tu portal a la configuración local de AdGuard; no se puede enumerar.**

## Mantenedores — actualización local

```bash
pip install -r requirements.txt
python scripts/build.py --out whitelist.txt
git diff  # revisar
git add whitelist.txt && git commit -m "chore: refresh whitelist"
```

`whitelist.txt` es **generado** — nunca lo edites a mano. Para añadir un dominio, edita el YAML fuente o amplía el parser.

## Añadir un nuevo servicio

1. Suelta un YAML en `sources/<servicio>.yaml` (consulta `sources/microsoft-teams.yaml` para el esquema).
2. Elige un parser:
   - **Catálogo legible por máquina** (ej. JSON): usa `json_endpoint` (o añade un nuevo parser en `scripts/lib/parsers/`, replicando `parsers/json_endpoint.py`) y referéncialo mediante `fetch.type`.
   - **Lista curada a mano** (sin catálogo upstream): usa `static_list` con `fetch: false` y un bloque `urls:`. Consulta `sources/netiq.yaml` para el esquema. **Añade un comentario por entrada citando la URL fuente** para que la lista siga siendo auditable.
3. Ejecuta `python scripts/build.py --out whitelist.txt` y revisa el diff.

## Pruebas

```bash
ruff check scripts/
python -m pytest -v
```

## Calendario de actualización

Una GitHub Action semanal vuelve a ejecutar la build y abre un PR si la salida cambió. Actualización manual:

```bash
gh workflow run refresh-whitelist.yml
```

## Estructura del repositorio

```
sources/                  # un YAML por servicio (URL del proveedor + config del parser)
scripts/build.py          # punto de entrada
scripts/lib/{lint,resolve,fetch}.py
scripts/lib/parsers/      # un módulo por familia de fuente
scripts/test/             # suite pytest + fixtures
whitelist.txt             # GENERADO. No editar.
.github/workflows/        # test + refresh
```

## Advertencias

- La API del catálogo de Microsoft 365 requiere un parámetro de query `?ClientRequestId=<UUID>`. Ambos YAMLs fuente incluyen un ID de cliente fijo para seguimiento; puedes cambiarlo, pero el parámetro debe ser un GUID válido.
- Muchas entradas del catálogo (ej. `*.static.microsoft`, `*.usercontent.microsoft`) no resuelven mediante DNS público, por lo que la build las descarta. Probablemente las sirva un CNAME comodín que 1.1.1.1 / 8.8.8.8 no puede ver. Filosofía de alcance dirigido: si no podemos verlo, no podemos añadirlo.
- **Los FQDNs específicos del despliegue no están incluidos.** El propio headend VPN/portal del cliente (ej. `vpn.ejemplo.com`, portal GlobalProtect) siempre es necesario pero no puede ser enumerado por una allowlist genérica. Añade esas entradas a tu configuración local de AdGuard.
- La build depende de que `pip install` tenga éxito. En hosts Debian, el Python del sistema está bloqueado por PEP 668 — usa un venv (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`).
