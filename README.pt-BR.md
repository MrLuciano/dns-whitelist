<p>
  <b>English</b> | <a href="README.pt-BR.md">Português (Brasil)</a> | <a href="README.fr.md">Français</a> | <a href="README.es.md">Español</a>
</p>

# dns-whitelist

Lista de permissões (allowlist) curada de nomes DNS consumida pelo **AdGuard Home**, mantida atualizada por uma build automatizada que obtém catálogos publicados pelos fornecedores.

## Consumir

AdGuard Home → Filtros → Listas de permissão DNS → Adicionar lista de bloqueio → URL:

```
https://raw.githubusercontent.com/MrLuciano/dns-whitelist/main/whitelist.txt
```

## O que faz

- **Busca catálogos ao vivo dos fornecedores** (catálogo de endpoints do Microsoft 365) semanalmente e em disparo manual; extrai os domínios que o Teams e o Microsoft Authenticator precisam.
- **Carrega listas YAML curadas manualmente** (Google Authenticator, NetIQ, Cisco AnyConnect, Palo Alto GlobalProtect) — para serviços que não publicam uma allowlist legível por máquina. Veja `sources/*.yaml` para os conjuntos de FQDNs curados e a documentação de origem que eles referenciam.
- Valida cada candidato com regras estritas de sintaxe no estilo RFC-1035.
- Remove domínios que não resolvem (eles não podem estar em nenhuma colisão de blocklist se não existem, então não pertencem a uma allowlist *direcionada*).
- Emite um `whitelist.txt` determinístico no formato de allowlist do AdGuard (`@@||dominio.com^`), com uma seção por serviço.

Atualmente coberto:

- **Microsoft Teams** — `serviceArea=Skype` no catálogo do Microsoft 365
- **Microsoft Authenticator** — `serviceArea=Common` no catálogo do Microsoft 365
- **Google Authenticator** — aplicativo offline-first; apenas o caminho de sincronização na nuvem precisa de rede. Curado manualmente.
- **NetIQ** (Access Manager + Identity Manager) — apenas os endpoints opcionais de atualização/registro/catálogo são do fornecedor. Curado manualmente.
- **Cisco AnyConnect / Secure Client** — domínios universais de suporte mais endpoints de nuvem do Umbrella e Secure Access. Curado manualmente.
- **Palo Alto GlobalProtect** — apenas o FQDN do portal do cliente é sempre necessário; fornecemos os endpoints opcionais de nuvem do Prisma Access / CIE / SLS. Curado manualmente. **Adicione o FQDN do seu portal à configuração local do AdGuard; ele não pode ser enumerado.**

## Mantenedores — atualização local

```bash
pip install -r requirements.txt
python scripts/build.py --out whitelist.txt
git diff  # revisar
git add whitelist.txt && git commit -m "chore: refresh whitelist"
```

`whitelist.txt` é **gerado** — nunca edite à mão. Para adicionar um domínio, edite o YAML de origem ou estenda o parser.

## Adicionar um novo serviço

1. Adicione um YAML em `sources/<servico>.yaml` (veja `sources/microsoft-teams.yaml` para o esquema).
2. Escolha um parser:
   - **Catálogo legível por máquina** (ex. JSON): use `json_endpoint` (ou adicione um novo parser em `scripts/lib/parsers/`, espelhando `parsers/json_endpoint.py`) e referencie-o via `fetch.type`.
   - **Lista curada manualmente** (sem catálogo upstream): use `static_list` com `fetch: false` e um bloco `urls:`. Veja `sources/netiq.yaml` para o esquema. **Adicione um comentário por entrada citando a URL de origem** para que a lista permaneça auditável.
3. Execute `python scripts/build.py --out whitelist.txt` e revise o diff.

## Testes

```bash
ruff check scripts/
python -m pytest -v
```

## Cronograma de atualização

Uma GitHub Action semanal executa a build novamente e abre um PR se a saída mudou. Atualização manual:

```bash
gh workflow run refresh-whitelist.yml
```

## Estrutura do repositório

```
sources/                  # um YAML por serviço (URL do fornecedor + config do parser)
scripts/build.py          # ponto de entrada
scripts/lib/{lint,resolve,fetch}.py
scripts/lib/parsers/      # um módulo por família de origem
scripts/test/             # suíte pytest + fixtures
whitelist.txt             # GERADO. Não edite.
.github/workflows/        # test + refresh
```

## Ressalvas

- A API do catálogo do Microsoft 365 requer um parâmetro de query `?ClientRequestId=<UUID>`. Ambos os YAMLs de origem incluem um ID de cliente fixo para rastreamento; você pode alterá-lo, mas o parâmetro deve ser um GUID válido.
- Muitas entradas do catálogo (ex. `*.static.microsoft`, `*.usercontent.microsoft`) não resolvem via DNS público, então são removidas pela build. Provavelmente são servidas por um CNAME coringa que o 1.1.1.1 / 8.8.8.8 não consegue ver. Filosofia de escopo direcionado: se não conseguimos ver, não conseguimos adicionar.
- **FQDNs específicos de implantação não estão incluídos.** O próprio headend VPN/portal do cliente (ex. `vpn.exemplo.com`, portal GlobalProtect) é sempre necessário mas não pode ser enumerado por uma allowlist genérica. Adicione essas entradas à sua configuração local do AdGuard.
- A build depende de `pip install` ser bem-sucedido. Em hosts Debian, o Python do sistema está bloqueado por PEP 668 — use um venv (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`).
