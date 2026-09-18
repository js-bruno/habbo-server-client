# Manual da Feature de Convite (Invite)

Feature que permite a um usuário criar outro usuário através de um link de
convite. O convidado escolhe só o nome; o sistema gera a senha, mostra na tela
e já manda direto pro client (auto-login via SSO).

---

## 1. Fluxo (visão do usuário)

### Quem convida
1. Entra em **/user/me** (página "Meu perfil") e clica no botão **"Invite friends"**.
   Também pode ir direto em **/user/invite**.
2. Define quantos usos o link aceita (padrão 1) e clica **Generate**.
3. Aparece o link pronto: `https://hotel.thisdev.space/invite/<codigo>` — copia e
   manda pra quem quiser. A lista abaixo mostra os convites já gerados, quem usou
   e quantos usos restam.

### Quem é convidado
1. Clica no link → abre a tela **"You have been invited!"** com um único campo:
   **Username** (e o checkbox de aceitar as regras).
2. Escolhe o nome e clica **Create my account**.
3. O sistema cria a conta, faz login automático e mostra a tela de sucesso com:
   - **Username** e **Password** gerada (10 caracteres, sem símbolos)
   - Botão **Copy credentials** (copia `usuario:senha`)
   - Botão **Enter the hotel** → abre o client Nitro já logado (SSO)
4. Se der refresh na tela de sucesso, a senha **some** (é mostrada uma única vez,
   de propósito). Se esquecer, é só usar "forgot password" com o e-mail... que
   não existe (conta criada sem e-mail) — **guarde a senha antes de sair da tela**.

> Link com `max_uses` > 1 permite várias criações com o mesmo código.

---

## 2. Rotas

| Método | Rota | Middleware | Função |
|---|---|---|---|
| GET | `/user/invite` | auth | Painel do convidador (gerar + listar) |
| POST | `/user/invite` | auth | Gera um novo convite (`max_uses`) |
| GET | `/invite/{code}` | guest | Página pública: escolher username |
| POST | `/invite/{code}` | guest | Cria a conta (redeem) |
| GET | `/user/invite/success` | auth | Mostra a senha gerada (1x) |

- `{code}`: 12 caracteres minúsculos aleatórios (`[a-z0-9]+`).
- Convite inexistente → **404**; expirado ou esgotado → **410**.

---

## 3. Arquivos (onde está o código)

Todos em `~/projects/habbo-dev/cms/`:

| Arquivo | Papel |
|---|---|
| `app/Http/Controllers/User/InviteController.php` | Toda a lógica (gerar, mostrar, redeem, sucesso) |
| `app/Services/GameUserMirror.php` | Espelha o usuário do CMS no banco do jogo |
| `app/Models/Invite.php` | Model Eloquent da tabela `invites` |
| `database/migrations/2026_09_18_000001_create_invites_table.php` | Cria a tabela |
| `config/database.php` | Conexão `game` (banco `habbo`) |
| `routes/web.php` | As 5 rotas acima |
| `resources/themes/atom/views/invite.blade.php` | Tela pública (username) — tema atom |
| `resources/themes/atom/views/invite-success.blade.php` | Tela da senha — tema atom |
| `resources/themes/atom/views/user/invite.blade.php` | Painel do convidador — tema atom |
| `resources/themes/dusk/views/...` (mesmos 3 nomes) | Idem — tema **dusk** (o ativo em produção) |
| `resources/themes/{atom,dusk}/views/user/me.blade.php` | Botão "Invite friends" |
| `test-invite.py` | Teste automatizado do fluxo (raiz do habbo-dev) |

---

## 4. Modelo de dados (tabela `invites` — banco `orioncms`)

```sql
CREATE TABLE `invites` (
  `id`         bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `code`       varchar(32) NOT NULL,               -- UNIQUE
  `inviter_id` int(11) DEFAULT NULL,               -- FK -> users.id (quem convidou)
  `used_by`    int(11) DEFAULT NULL,               -- FK -> users.id (último que usou)
  `max_uses`   int(11) NOT NULL DEFAULT 1,
  `expires_at` timestamp NULL DEFAULT NULL,        -- NULL = nunca expira
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `used_at`    timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`)
)
```

Criada manualmente no shatterdome (a migration é a fonte). Observações que
mordem quem recriar:

- `orioncms.users.id` é **INT(11) signed** — a FK deve ser `integer()` signed
  (unsigned dá erro 1005).
- `orioncms.users` é `utf8mb3_general_ci` — tabela nova com FK precisa do
  **mesmo charset** (senão erro 150).

---

## 5. O que o redeem faz por baixo (importante)

O registro normal do CMS (Fortify `CreateNewUser`) exige e-mail, Turnstile e
respeita `max_accounts_per_ip` — nada disso se aplica ao convite. O redeem:

1. Valida o convite (existe? expirado? esgotado?).
2. Valida o username (regex do setting `username_regex`, máx. 25, único,
   wordfilter).
3. Gera senha: `Str::password(10, symbols: false)`.
4. Cria o usuário em `orioncms.users` (mail = NULL — a coluna é nullable).
5. **Espelha no banco do jogo** via `GameUserMirror`: `habbo.users` +
   `users_settings` + `users_currency` (duckets 5000, diamantes 100).
   > Sem esse espelho o jogador é desconectado com "Bye" logo após o handshake
   > do websocket — o emulador só lê `habbo.users`.
6. Marca o convite como usado (`used_by` + `used_at`).
7. `Auth::login` + redirect pro success com a senha em flash.

---

## 6. Testando

Teste automatizado de ponta a ponta (login → gerar → abrir com sessão limpa →
criar → conferir espelho → cleanup):

```bash
cd ~/projects/habbo-dev
nix shell --impure --expr 'with import <nixpkgs> {}; python3.withPackages (ps: [ ps.requests ])' \
  -c env ADMIN_USER=<usuario> ADMIN_PASS='<senha>' ./test-invite.py
```

Esperado (todas as linhas `[ok]`):

```
[ok] login admin
[ok] convite gerado: <code>
[ok] pagina do convite renderiza
[ok] usuario criado, redirect -> .../user/invite/success
[ok] senha exibida: ***
[ok] espelho habbo.users: <id> <username> LEGACY 1
[ok] users_settings: <id>
[ok] users_currency: 0 5000 | 5 100
[ok] cleanup
FLUXO COMPLETO OK
```

Manual rápido (curl, sem CSRF):
- `curl -s -o /dev/null -w '%{http_code}' -H 'Host: caravelho.com.br' http://localhost/user/invite` → **302** (sem login)
- `curl -s -o /dev/null -w '%{http_code}' -H 'Host: caravelho.com.br' http://localhost/invite/codigoqualquer` → **404** (inexistente)
- Código real → **200** com "You have been invited!"

---

## 7. Deploy

Não precisa rebuildar nada: o vhost nginx serve `~/projects/habbo-dev/cms`
diretamente (symlink `/var/www/habbo`). Editar → testar → commit + push:

```bash
cd ~/projects/habbo-dev
git add -A && git commit -m "..." && git push origin main
```

Se mexer em rotas/controllers, limpar a rota cache se existir:
```bash
cd cms && php artisan route:clear && php artisan view:clear
```
(E o restart do phpfpm se o OPcache segurar bytecode antigo:
`sudo systemctl restart phpfpm-habbo`.)

---

## 8. Problemas conhecidos

| Sintoma | Causa | Fix |
|---|---|---|
| `View [user.invite] not found` | Tema ativo é `dusk` (setting `website_settings.theme`), view criada só no atom | Criar a view nos DOIS temas |
| 500 no redeem com `Data truncated for column 'mail_verified'` | `habbo.users.mail_verified` é `enum('0','1')`; int 0 estoura | Passar string `'0'`/`'1'` (GameUserMirror já faz) |
| 500 com `1048 mail_verified cannot be null` | Passou null em coluna NOT NULL | Nunca passar null; usar `'0'` |
| 500 com `1005` ao criar tabela `invites` | FK signed/unsigned ou charset divergente | `integer()` signed + utf8mb3 |
| Convidado cai com "Bye" no client | Usuário não espelhado em `habbo.users` | Conferir `GameUserMirror` rodou (log ou test-invite.py) |
| Senha não aparece no refresh | Proposital (flash de 1 vez) | Copiar antes; não há e-mail pra recuperar |
| Link abre mas redireciona pra /user/me | Você está logado (middleware guest) | Abrir em aba anônima / deslogar |
| Teste com `requests` quebra resolvendo `caravelho.com.br` | DNS do domínio não resolve no nix shell | Sempre `BASE=http://localhost` + header `Host` |

---

## 9. Ideias de evolução

- **E-mail opcional** no passo do username (hoje mail é NULL; forgot password
  não funciona para convidados).
- **Link de convite com validade** (`expires_at` já existe na tabela, falta
  campo na tela de gerar).
- **Recompensa ao convidador** (ex.: diamantes quando o convite for usado) —
  reusar o padrão `recordReferral` do CreateNewUser.
- **Criar o usuário no client direto** (sem passar pela tela de senha): já é
  quase isso — dá pra pular o success com um redirect pro nitro passando o SSO.
- **Listar convidados** no painel (quem usou, quando, se está online).

---

*Feature: commit `3a0b925` no repo `habbo-server-client` (branch main).*