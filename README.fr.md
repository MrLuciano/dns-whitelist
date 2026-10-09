<p>
  <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (Brésil)</a> | <b>Français</b> | <a href="README.es.md">Español</a>
</p>

# dns-whitelist

Liste d'autorisation (allowlist) soignée de noms DNS consommée par **AdGuard Home**, maintenue à jour par un build automatisé qui récupère les catalogues publiés par les éditeurs.

## Consommer

AdGuard Home → Filtres → Listes d'autorisation DNS → Ajouter une blocklist → URL :

```
https://raw.githubusercontent.com/MrLuciano/dns-whitelist/main/whitelist.txt
```

## Ce que ça fait

- **Récupère les catalogues officiels des éditeurs** (catalogue d'endpoints Microsoft 365) chaque semaine et sur déclenchement manuel ; extrait les domaines dont Teams et Microsoft Authenticator ont besoin.
- **Charge des listes YAML curées à la main** (Google Authenticator, NetIQ, Cisco AnyConnect, Palo Alto GlobalProtect) — pour les services qui ne publient pas d'allowlist lisible par machine. Voir `sources/*.yaml` pour les ensembles de FQDNs curés et la documentation source qu'ils référencent.
- Valide chaque candidat avec des règles de syntaxe strictes de type RFC-1035.
- Élimine les domaines qui ne résolvent pas (ils ne peuvent pas être en collision avec une blocklist s'ils n'existent pas, donc ils n'ont pas leur place dans une allowlist *ciblée*).
- Émet un `whitelist.txt` déterministe au format allowlist d'AdGuard (`@@||domaine.com^`), avec une section par service.

Actuellement couvert :

- **Microsoft Teams** — `serviceArea=Skype` dans le catalogue Microsoft 365
- **Microsoft Authenticator** — `serviceArea=Common` dans le catalogue Microsoft 365
- **Google Authenticator** — application hors-ligne d'abord ; seul le chemin de synchronisation cloud nécessite le réseau. Curé à la main.
- **NetIQ** (Access Manager + Identity Manager) — seuls les endpoints optionnels de mise à jour/enregistrement/catalogue appartiennent à l'éditeur. Curé à la main.
- **Cisco AnyConnect / Secure Client** — domaines universels de support plus endpoints cloud Umbrella et Secure Access. Curé à la main.
- **Palo Alto GlobalProtect** — seul le FQDN du portail client est toujours requis ; nous fournissons les endpoints cloud optionnels Prisma Access / CIE / SLS. Curé à la main. **Ajoutez le FQDN de votre portail à la configuration locale d'AdGuard ; il ne peut pas être énuméré.**

## Mainteneurs — mise à jour locale

```bash
pip install -r requirements.txt
python scripts/build.py --out whitelist.txt
git diff  # examiner
git add whitelist.txt && git commit -m "chore: refresh whitelist"
```

`whitelist.txt` est **généré** — ne jamais l'éditer à la main. Pour ajouter un domaine, modifiez le YAML source ou étendez le parser.

## Ajouter un nouveau service

1. Ajoutez un YAML dans `sources/<service>.yaml` (voir `sources/microsoft-teams.yaml` pour le schéma).
2. Choisissez un parser :
   - **Catalogue lisible par machine** (ex. JSON) : utilisez `json_endpoint` (ou ajoutez un nouveau parser dans `scripts/lib/parsers/`, en miroir de `parsers/json_endpoint.py`) et référencez-le via `fetch.type`.
   - **Liste curée à la main** (pas de catalogue amont) : utilisez `static_list` avec `fetch: false` et un bloc `urls:`. Voir `sources/netiq.yaml` pour le schéma. **Ajoutez un commentaire par entrée citant l'URL source** pour que la liste reste auditable.
3. Lancez `python scripts/build.py --out whitelist.txt` et examinez le diff.

## Tests

```bash
ruff check scripts/
python -m pytest -v
```

## Calendrier de rafraîchissement

Une GitHub Action hebdomadaire relance le build et ouvre une PR si la sortie a changé. Rafraîchissement manuel :

```bash
gh workflow run refresh-whitelist.yml
```

## Structure du dépôt

```
sources/                  # un YAML par service (URL éditeur + config parser)
scripts/build.py          # point d'entrée
scripts/lib/{lint,resolve,fetch}.py
scripts/lib/parsers/      # un module par famille de source
scripts/test/             # suite pytest + fixtures
whitelist.txt             # GÉNÉRÉ. Ne pas éditer.
.github/workflows/        # test + refresh
```

## Réserves

- L'API du catalogue Microsoft 365 requiert un paramètre de query `?ClientRequestId=<UUID>`. Les deux YAMLs sources incluent un ID client fixe pour le suivi ; vous pouvez le changer, mais le paramètre doit être un GUID valide.
- De nombreuses entrées du catalogue (ex. `*.static.microsoft`, `*.usercontent.microsoft`) ne résolvent pas via le DNS public, et sont donc éliminées par le build. Elles sont probablement servies par un CNAME wildcard que 1.1.1.1 / 8.8.8.8 ne peut pas voir. Philosophie de portée ciblée : si on ne peut pas le voir, on ne peut pas l'ajouter.
- **Les FQDNs spécifiques au déploiement ne sont pas inclus.** Le propre headend VPN/portail du client (ex. `vpn.exemple.com`, portail GlobalProtect) est toujours requis mais ne peut pas être énuméré par une allowlist générique. Ajoutez ces entrées à votre configuration locale d'AdGuard.
- Le build dépend de la réussite de `pip install`. Sur les hôtes Debian, le Python système est verrouillé par PEP 668 — utilisez un venv (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`).
