# habbo-dev — Guia de Conhecimento Completo (para consumo por IA)

Stack de **Habbo Retro** (servidor privado estilo Habbo) rodando no NixOS **sem devenv**:
MySQL/MariaDB (systemd) + Arcturus Morningstar 3.5.5 (emulador Java 17) + Atom CMS
(Laravel, PHP 8.5) servido por nginx + php-fpm em **modo produção** + client
**Nitro (nitro-react)** servido pelo próprio CMS.

Este guia é autocontido: com ele, outra IA consegue recriar o servidor do zero e
diagnosticar os problemas já conhecidos. Todas as seções vêm de troubleshooting REAL
feito nesta máquina.

---

## 1. Arquitetura — as peças

| Serviço | O que é | Tech | Porta | Onde |
|---|---|---|---|---|
| MySQL | Banco do jogo + CMS | MariaDB 10.11 (systemd, NixOS) | 3306 | `services.mysql` no nix-config |
| Arcturus Morningstar 3.5.5 | Emulador ("servidor do jogo") | Java 17 (JAR uber) | **3000 game TCP**, **2096 websocket Nitro**, 3560 RCON | `arcturus/Habbo-3.5.5-jar-with-dependencies.jar` |
| Atom CMS (a.k.a. Orion) | Site: registro, login, housekeeping, serve o client | Laravel 13, PHP 8.5 | 80 (nginx) | `cms/`, symlink `/var/www/habbo → ~/projects/habbo-dev/cms` |
| nginx + php-fpm | Servir o CMS | nginx 1.30 + php-fpm pool `habbo` (php85) | 80/443 | vhost `caravelho.com.br` |
| Nitro client | Client HTML5 do jogo | nitro-react (vite build) | servido via nginx em `/client/` | `cms/public/client/` |

**Portas REAIS (validado com `ss -tlnp`)**: 3306 MySQL · **3000 game TCP** ·
**2096 Nitro websocket** · 3560 RCON (loopback) · 80 nginx. O game TCP e o
websocket são portas DIFERENTES de propósito: o plugin ms-websockets faz o próprio
`bind()` e conflita se usar a mesma porta do game.

Fluxo real: `mysql.service` (NixOS) → `habbo-arcturus.service` (systemd, `java -jar`)
conecta no 3306 → nginx serve o CMS em `http://localhost/` (vhost `caravelho.com.br`)
→ usuário clica "start game" → CMS gera ticket SSO → iframe `/client/index.html?sso=...`
→ client abre websocket `ws://<host>:2096` → autentica no emulador.

---

## 2. Onde vive a configuração (nix-config, NÃO o devenv)

Repositório: `~/.config/nix-config` (git, flake). Host: `server` (hostname `shatterdome`).
Rebuild: `sudo nixos-rebuild switch --flake .#server`.

Arquivos relevantes:
- `hosts/server/configuration.nix` — user `gipsydanger` com `homeMode = "755"`
  (nginx precisa ler o home via symlink); pool `services.phpfpm.pools.habbo` com
  `phpPackage = pkgs.php85` e `listen.owner/group = nginx, listen.mode = 0660`.
  Adiciona `systemd.services.phpfpm-habbo.serviceConfig.ProtectHome = lib.mkForce false`.
- `hosts/server/services/habbo.nix` — `systemd.services.habbo-arcturus`:
  `ExecStart = "${pkgs.jdk17}/bin/java -jar ${arcturusJar}"`,
  `WorkingDirectory = arcturusDir`, `User = "gipsydanger"`, `Restart = "on-failure"`,
  `After = mysql.service`.
- `hosts/server/services/nginx.nix` — vhost `caravelho.com.br`, root
  `/var/www/habbo/public`, try_files → `/index.php`, fastcgi no socket do pool;
  `systemd.services.nginx.serviceConfig.ProtectHome = lib.mkForce false`;
  **sub_filters do client** (ver seção 7.4).
- `hosts/server/services/mysql.nix` — MariaDB 10.11 (`pkgs.mariadb_1011`),
  `initialDatabases = [{ name = "habbo"; }]`, initialScript cria user `habbo`
  (mas `CREATE USER IF NOT EXISTS` NÃO altera senha de user existente — o user real
  continua com a senha definida manualmente).
- `hosts/server/network-local.nix` — firewall libera 2096, 3000, 3306, 80, 443.

**IMPORTANTE — ProtectHome**: o systemd do NixOS aplica `ProtectHome=true` em nginx e
php-fpm por padrão. Isso bloqueia a leitura de `/home` MESMO com permissões corretas.
Sem o `lib.mkForce false` (adicionado em ambos), o CMS dá 404 "Primary script unknown"
ou `stat() failed (13: Permission denied)`.

---

## 3. Credenciais / portas

- **`.env` do cms é secret-bearing — nunca ler em texto puro** (usar grep com filtro
  ou redigir `s/(PASSWORD|KEY|SECRET)=.*/\1=***/I`).
- Banco do jogo: db `habbo`, user `habbo`, senha `9911` (definida no `arcturus/config.ini`).
- CMS: `DB_DATABASE=orioncms`, mesmo user `habbo`. Bancos: `habbo` (schema Arcturus,
  123 tabelas) + `orioncms` (Laravel/atom).
- `config.ini` do Arcturus (chaves REAIS): `db.hostname=localhost`,
  `game.host = 0.0.0.0`, `game.port = 3000`, `rcon.host=127.0.0.1`, `rcon.port=3560`,
  `rcon.allowed=127.0.0.1`, `rcon.enabled=false` (RCON sobe incondicionalmente no
  3.5.5 — `new RCONServer` sem checar config). **NÃO usar `game.tcp.port` /
  `game.tcp.bindip` / `rcon.allowedaddress` — o 3.5.5 não lê essas chaves.**
- CMS `.env` (produção): `APP_ENV=production`, `APP_DEBUG=false`,
  `APP_URL=http://caravelho.com.br`, `SESSION_DOMAIN=` (vazio — host-only, evita 419),
  `EMULATOR_PORT=2096` (!! o websocket, NÃO o game port), `FORCE_HTTPS=false`.

Acesso MySQL como app user (sem sudo):
```bash
DBPASS=$(grep -E "^db.password" arcturus/config.ini | cut -d= -f2 | tr -d ' ')
MYSQL_PWD="$DBPASS" mysql -h 127.0.0.1 -u habbo habbo -e "..."
```

---

## 4. Bootstrap do ZERO (receita validada)

### 4.1 Banco
1. `sudo mysql -e "CREATE DATABASE habbo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER 'habbo'@'localhost' IDENTIFIED BY '9911'; GRANT ALL ON habbo.* TO 'habbo'@'localhost';"` (idem `orioncms` + grants em 127.0.0.1)
2. **Collation fix obrigatório** (MySQL 8 → MariaDB 10.11):
   `sed 's/utf8mb4_0900_ai_ci/utf8mb4_unicode_ci/g' arcturus/base_arcturus.sql | sudo mysql habbo`
   Sem isso: `ERROR 1273 Unknown collation: 'utf8mb4_0900_ai_ci'`.
3. **`chat_bubbles` NÃO existe no base_arcturus.sql** — o JAR 3.5.5 executa
   `SELECT * FROM chat_bubbles` no boot e morre. Criar a partir de
   `arcturus/sqlupdates/Update 3_5_3 to 3_5_4.sql` (pré-requisito: colunas
   `acc_unignorable` e `cmd_update_chat_bubbles` em `permissions`).

### 4.2 CMS (Atom/Orion, Laravel 13)
```bash
cd cms
nix shell nixpkgs#php85Packages.composer -c composer install --no-interaction   # NUNCA "php composer" (ELF nativo)
nix shell nixpkgs#php85 -c php artisan atom:install --no-interaction   # 1ª vez; exige bancos pré-criados + collation fix
# produção: config:cache, route:cache, view:cache, event:cache (rodar DEPOIS de qualquer mudança no .env)
```
- PHP 8.5 é OBRIGATÓRIO (vendor usa sintaxe 8.5-only). Sistema default (8.3/8.4)
  quebra com `syntax error, unexpected token "->"` em
  `vendor/symfony/var-dumper/Cloner/VarCloner.php:90`.
- Composer correto: `nix shell nixpkgs#php85Packages.composer -c composer` (o composer
  do sistema embute PHP 8.3 e falha o platform-check).
- **Turnstile**: a validação server-side é incondicional em 6 arquivos
  (`app/Actions/Fortify/CreateNewUser.php` + 5 `app/Http/Requests/*.php`):
  `'cf-turnstile-response' => [app(Turnstile::class)]` → TypeError 500 em todo
  POST de login/registro sem token. Fix nos 6: `['sometimes', 'nullable', 'string',
  app(Turnstile::class)]` (`nullable` obrigatório — `ConvertEmptyStringsToNull`
  transforma vazio em null). Depois: restart do phpfpm (OPcache).
- `max_accounts_per_ip` (website_settings, default 2) bloqueia registros de teste
  com "maximum allowed accounts" — subir (ex. 10) para testes.

### 4.3 Emulador (Arcturus 3.5.5)
1. `config.ini` com as chaves da seção 3.
2. Boot check: `timeout 50 java -jar Habbo-3.5.5-jar-with-dependencies.jar` →
   esperar `Database -> Connected!` + `Started GameServer on 0.0.0.0:3000` +
   RCON 3560. Logs reais: `arcturus/logging/errors/runtime.txt` (o journald é
   inundado por "Waiting for command" — não usar journald para debug).
3. Systemd unit `habbo-arcturus` (nix-config, seção 2).

### 4.4 Plugin Nitro Websockets (ms-websockets)
1. Maven, única dependência `com.eu.habbo:Habbo:*` — NÃO está no Maven Central:
   ```bash
   mvn install:install-file -Dfile=<emulador-jar> -DgroupId=com.eu.habbo -DartifactId=Habbo -Dversion=3.0.0
   mvn package
   ```
2. Copiar jar para `arcturus/plugins/` + restart. No boot, registra
   `ws.nitro.host`, `ws.nitro.port`, `ws.nitro.ip.header`, `websockets.whitelist`
   em `emulator_settings` (as linhas só aparecem APÓS o restart).
3. Se `game.port` == `ws.nitro.port`: `BindException: Endereço já em uso` no boot,
   plugin morto, service "ativo" mas handshake nunca completa. Portas separadas
   (esta máquina: game=3000, ws=2096) + checar log `Nitro Websockets Listening on ws://...`.

### 4.5 SSO entre CMS e emulador (trigger MySQL)
CMS e emulador usam bancos separados. O CMS escreve `auth_ticket` em
`orioncms.users`; o emulador busca em `habbo.users` (`SELECT ... WHERE auth_ticket=?`).
- Todo user do CMS precisa de um twin em `habbo.users` (username/look/gender/rank/credits).
- **Trigger** `AFTER UPDATE` em `orioncms.users` copia `auth_ticket` para
  `habbo.users` por username. Sem isso: client fecha com SSO inválido silenciosamente.
- Ticket é de USO ÚNICO e expira: novo login no CMS gera ticket novo. No iframe
  recarregado com ticket velho, a autenticação falha.

### 4.6 Assets e client Nitro (a parte mais longa)
O nitro é QUATRO repos:
1. **nitro-client** (billsonnn/nitro-react) — build com vite, `base: './'` no
   `vite.config.js` (senão os refs absolutos `/assets/...` quebram sob `/client/`).
2. **nitro-converter** (SWF → .nitro) — converter FigureMap/effects/pets a partir
   dos SWFs do pack.
3. **Asset packs** (default-assets + arcturus-morningstar-default-swf-pack) — 1.6G.
4. **ms-websockets** (seção 4.4).

Receita validada:
```bash
cd nitro-client
yarn install
# ANTES do build: editar index.html → config.urls RELATIVOS (ver 7.2)
yarn build        # output em dist/
cp -r dist/* cms/public/client/   # NÃO apagar renderer-config.json/ui-config.json/gamedata — reaplicar depois
```
- Converter: converter os SWFs LOCALMENTE (máquina antiga — não paralelizar,
  timeouts generosos). Pets: SWFs de pet NÃO estão no pack (fallback placeholder,
  inofensivo).
- `gamedata/UITexts.json` e `HabboAvatarActions.json` vêm do default-assets e PRECISAM
  ser copiados para `cms/public/client/gamedata/` — sem eles, o loading trava (ver 7.5).

### 4.7 Configs do client (pós-cópia)
`cms/public/client/renderer-config.json`:
- `socket.url` = `ws://<host>:2096` (dinâmico via sub_filter do nginx, seção 7.4)
- `asset.url` = `http://<host>/client` (senão 404 em gamedata/bundled/c_images)
- `image.library.url` e `hof.furni.url` idem.

`cms/public/client/ui-config.json`:
- `url.prefix` = `http://<host>` e `camera.url` = `http://<host>/client/camera/`.

**CUIDADO**: `cp -r dist/*` SOBRESCREVE configs editados (o dist original traz
`wss://ws.website.com:2096` e `https://website.com` de exemplo). Re-aplicar os
configs depois de cada cópia. Verificar com teste por Host (seção 7.4).

---

## 5. Problemas reais já diagnosticados (resumo por sintoma)

| Sintoma | Causa raiz | Fix |
|---|---|---|
| `wrong space ID` InnoDB (devenv) | bootstrap MariaDB morto no meio (I/O lento + readiness probe) | abandonar devenv; usar mysql.service do NixOS |
| 500 no CMS | PHP 8.3 + vendor 8.5-only | pool php85 + composer via php85Packages |
| `Unknown collation utf8mb4_0900_ai_ci` | schema MySQL 8 em MariaDB 10.11 | sed de collation no import |
| Emulador morre no boot | `chat_bubbles` ausente | update 3_5_3→3_5_4.sql |
| `Config key not found game.host/game.port` | chaves erradas no config.ini | `game.host`/`game.port` (não `game.tcp.*`) |
| 419 Page Expired | SESSION_DOMAIN fixo ≠ Host | `SESSION_DOMAIN=` vazio + limpar cookies |
| 502/404/stat permission denied | ProtectHome + homeMode 700 + socket fpm | ProtectHome=false em nginx+fpm, homeMode 755, listen 0660 |
| 500 em login/registro | Turnstile incondicional no server | `sometimes,nullable,string` nos 6 arquivos |
| "start game" abre frame vazio | nitro_path sem client em public/client | build + cópia para `cms/public/client/` |
| "connection failed" | socket.url fixo/errado + whitelist de origins | sub_filter + whitelist completa (7.3/7.4) |
| "configuration failed" | config.urls absolutos no index.html | `./renderer-config.json` relativo (7.2) |
| Loading trava em 20% | `gamedata/UITexts.json` 404 (localization) | copiar gamedata do default-assets (7.5) |
| Loading trava em 80% | handshake incompleto (7.6) | ver 7.6 |
| Rebuild sobrescreve configs | `cp -r dist/*` restaura `.example` | re-aplicar configs + teste por Host |

---

## 6. Armadilhas desta máquina (PC antigo)

- **I/O lento e imprevisível**: bootstrap do MariaDB e `npm install` ficam em
  **D-state** por minutos. Não rodar operações pesadas em paralelo.
- RAM 8GB: suficiente, mas não folgada.
- `sudo` sem TTY falha (timestamp ausente) — preferir `MYSQL_PWD=...` com o user app.
- `systemctl restart` + UPDATE no banco em sequência = **racing** (ver 7.3).

---

## 7. Troubleshooting detalhado do client Nitro (a saga)

### 7.1 Progresso do loading (App.tsx) — cada etapa vale 20%
1. 20%: `ConfigurationEvent.LOADED` + `localization.init()`
2. +20%: preload de assets
3. +20%: `CONNECTION_HANDSHAKING` (websocket abriu)
4. +20%: `CONNECTION_AUTHENTICATED` (SSO ok)
5. `ENGINE_INITIALIZED` +300ms → fim.

Diagnóstico por onde parou:
- **20%** → localization quebrou → checar `gamedata/UITexts.json` (404?)
- **80%** → websocket abriu, SSO pode ou não ter completado → checar 7.6
- Antes de 20% → configs → 7.2

### 7.2 "configuration failed"
- **Causa**: o `index.html` buildado carrega `NitroConfig` inline com
  `config.urls: ['/renderer-config.json', '/ui-config.json']` (absoluto). Servido
  sob `/client/`, o fetch resolve para a RAIZ do Laravel → 404 HTML →
  `response.json()` lança → `ConfigurationEvent.FAILED`.
- **Fix**: no FONTE (`index.html`), trocar para `'./renderer-config.json'` e
  `'./ui-config.json'` ANTES do `yarn build`. (vite `base: './'` NÃO reescreve
  strings embutidas no HTML — só os `<script src>`.)
- Verificar: GET `http://<host>/client/renderer-config.json` → 200 + `application/json`.

### 7.3 "connection failed" — whitelist de origins
- O plugin valida o header `Origin` do websocket contra `websockets.whitelist`
  (`CustomHTTPHandler`): fora da lista → 403 antes do upgrade.
- Default é `localhost` — adicionar TODOS os hosts de acesso
  (`localhost,192.168.15.50,caravelho.com.br`).
- **A whitelist REVERTE no boot**: o `register()` do plugin faz INSERT cego quando
  a chave não está no map em memória (o registro roda antes das emulator_settings
  carregarem). Fix definitivo:
  1. `systemctl stop habbo-arcturus` → `UPDATE emulator_settings SET value='...'`
     → `systemctl start` (**NUNCA restart** — racing sobrescreve).
  2. E/ou recompilar o plugin com `registerDefault()` (SELECT no banco antes de
     registrar — já implementado em `main.java`).
- Teste: `scripts/ws-browser-test.py` (Origins) — 101 nos hosts válidos, 403 no evil.

### 7.4 socket.url e assets por Host (sub_filter nginx)
Um único `renderer-config.json` em disco não serve hosts diferentes. O nginx
reescreve por request (no vhost, location `= /client/renderer-config.json`):
```nix
sub_filter_once on;
sub_filter_types application/json;
sub_filter 'ws://localhost:2096' 'ws://''${host}:2096';
sub_filter 'http://localhost/client/c_images/' 'http://''${host}/client/c_images/';
sub_filter 'http://localhost/client/dcr/hof_furni' 'http://''${host}/client/dcr/hof_furni';
```
No Nix (`''...''` string): só `''${host}` escapa a interpolação — `${host}` avalia
e `\${host}` fica literal. `sub_filter_once on` = só a 1ª ocorrência → usar
padrões COMPLETOS (padrões curtos não casam).
Depois do rebuild, TESTAR por cada Host (curl/urllib): o JSON deve trazer
`ws://<host>:2096` e assets com o host certo.

### 7.5 Loading trava em 20%
- `gamedata/UITexts.json` (e `HabboAvatarActions.json`) existem no default-assets
  mas não são copiados na montagem → 404 → `localization.init()` nunca resolve.
- Fix: copiar ambos para `cms/public/client/gamedata/` → 200.
- Outros 404s cosméticos (ex. `web_promo_small/*.png`, `storage/website_news_images`)
  NÃO travam o loading.

### 7.6 Loading trava em 80% (a mais difícil)
Sintomas observados:
- Client chega a 80% e para; console sem erros ("Nitro 2.2.0 - Renderer 1.6.6",
  "PixiJS WebGL2 OK"); `ss -tn` sem conexão estabelecida na 2096 depois de um tempo.
- `admin online=1` no banco MAS o client nunca chega a `ENGINE_INITIALIZED`.
- Log do emulador: `Plaintext received instead of ssl, closing channel`
  (uma `DecoderException` no `exceptionCaught` do `GameMessageHandler` — NÃO é TLS
  real) + `Config key not found encryption.forced` (inofensivo — chave ausente,
  `getBoolean(...,false)`).

Descobertas de wire protocol (testes com socket python + tickets frescos):
- **SSO puro (header 2419, 1 ou 2 campos) → 101 + frame ~1.7KB (autentica).**
- **QUALQUER packet antes do SSO (4000 ClientHello, 2490 UniqueID) → close frame
  1000 "Bye" imediato.** Todos os nitro-react (renderer 1.3.4 a 1.6.6) enviam
  ClientHello quase junto com o SSO (`NitroCommunicationDemo.ts`:
  `send(ClientHello)` + `tryAuthentication()` no mesmo tick).
- O emulador processa packets num thread pool (`MULTI_THREADED_PACKET_HANDLING`);
  na prática o SSO do browser chega a executar (user fica online) antes do close
  derrubar tudo → client preso em 80% esperando o resto do handshake que nunca vem.
- Reproduzir com cuidado: user deve estar `online=0` entre combos (segundo login do
  mesmo user com connect() → false → "Bye" falso positivo). Ticket FRESCO por tentativa
  (login no CMS via requests.Session → GET /game/nitro → parse do iframe `sso=`).

**Resolução observada na prática**: depois de TODOS os fixes acumulados (gamedata
copiado, configs relativos, sub_filters por host, whitelist persistida) + novas
tentativas de login, o jogo ABRIU e rodou com o client servido ainda sendo o build
vite (renderer 1.6.6) — sem precisar do downgrade. O downgrade para a tag 2.1.1
(renderer 1.3.4) foi feito e buildado (`nitro-client/build/`) mas NÃO foi implantado.
Conclusão: o 80% não era a versão do client; era o ecossistema (assets 404 +
configs errados + conexão caindo em tentativas anteriores). Se um novo servidor
travar em 80% com tudo o resto validado, investigar o 4000/2490-pré-SSO no pipeline
do plugin (GamePolicyDecoder/GameByteFrameDecoder/GameByteDecoder) como causa
remanescente.

### 7.7 Estado atual (última checagem)
- Services: mysql (3306), habbo-arcturus (game 3000 + ws 2096 + RCON 3560), nginx,
  phpfpm-habbo — todos ativos.
- Client servido: `cms/public/client/` (build vite, index-552ff3e4.js); nitro-client
  em checkout `2.1.1` (renderer 1.3.4) com `build/` pronto, não implantado.
- Acessos: `http://localhost/` ou `http://192.168.15.50/`; `caravelho.com.br` não
  resolve em DNS público (add ao /etc/hosts de outras máquinas para usar o nome).
- Login admin/admin123 rank 7; user `admin` online quando jogando.

---

## 8. Comandos úteis

```bash
# Estado
systemctl is-active mysql habbo-arcturus nginx phpfpm-habbo
ss -tlnp | grep -E ':(3000|2096|3560|3306|80)\b'
# Logs reais do emulador (journald é inútil — flood de "Waiting for command")
tail -30 arcturus/logging/errors/runtime.txt
# MySQL sem sudo
DBPASS=$(grep -E "^db.password" arcturus/config.ini | cut -d= -f2 | tr -d ' ')
MYSQL_PWD="$DBPASS" mysql -h 127.0.0.1 -u habbo habbo -e "SELECT username, online FROM users;"
# Teste websocket SSO (sem browser)
nix shell nixpkgs#python3 -c python3 scripts/ws-sso-test.py
# Whitelist (NUNCA restart — stop → UPDATE → start)
sudo systemctl stop habbo-arcturus
MYSQL_PWD="$DBPASS" mysql -h 127.0.0.1 -u habbo habbo -e \
  "UPDATE emulator_settings SET value='localhost,192.168.15.50,caravelho.com.br' WHERE \`key\`='websockets.whitelist';"
sudo systemctl start habbo-arcturus
# Rebuild NixOS
cd ~/.config/nix-config && sudo nixos-rebuild switch --flake .#server
# Cache do Laravel (settings do site ficam 9999999999s em Cache::rememberForever)
# → apagar storage/framework/cache/data + restart phpfpm
```

---

## 9. Fontes primárias consultadas

- `arcturus/src/main/java/com/eu/habbo/Emulator.java` e `ConfigurationManager.java`
  (chaves reais de config)
- `arcturus/sqlupdates/Update 3_5_3 to 3_5_4.sql` (chat_bubbles)
- `cms/app/Models/Miscellaneous/WebsiteInstallation.php` (tabela `website_installation`)
- Bytecode do jar 3.5.5 (`javap`): `PacketManager` (headers 4000/2419/2490,
  `@NoAuthMessage`), `SecureLoginEvent` (`encryption.forced` default false),
  `ChannelReadHandler` (packet ignorado sem GameClient), `GameMessageHandler`
  (exceptionCaught → close), `GameByteFrameDecoder` (EvaWire
  `[4B len][2B hdr][body]`, LengthFieldBasedFrameDecoder 417792/0/4/0/4)
- `ms-websockets/src/main/java/org/krews/plugin/nitro/websockets/NetworkChannelInitializer.java`
  (pipeline do ws: Http → CustomHTTPHandler → WebSocketProtocol → WebSocketCodec →
  GamePolicyDecoder → GameByteFrameDecoder → GameByteDecoder → RateLimit → GameMessageHandler)
- `node_modules/@nitrots/nitro-renderer/src/nitro/communication/demo/NitroCommunicationDemo.ts`
  (fluxo de handshake do client)