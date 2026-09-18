# Salas, Eventos e Mobília — Comandos

Guia para criar salas públicas decoradas e eventos no Atom Hotel, direto no
banco do jogo. Tudo em `~/projects/habbo-dev/scripts/`.

---

## 1. Comando rápido (tudo de uma vez)

Cria sala pública + decora com móveis de bom gosto + evento de 7 dias:

```bash
sudo bash scripts/create-themed-room.sh \
  "Sala de Jogos" model_s 6 6 \
  "Torneio de Jogos" "Vem jogar e competir!" 40
```

Argumentos:
| # | O quê | Exemplo |
|---|---|---|
| 1 | Nome da sala | "Sala de Jogos" |
| 2 | Modelo (ver lista abaixo) | model_s |
| 3 | Categoria pública (navigator) | 6 |
| 4 | Categoria do evento | 6 |
| 5 | Título do evento | "Torneio de Jogos" |
| 6 | Descrição | "Vem jogar!" |
| 7 | Máx. usuários (opcional) | 40 |

Depois reinicie o emulador para o navigator recarregar:

```bash
sudo systemctl restart habbo-arcturus
```

> A mobília aparece na 1ª visita à sala (o emulador lê `items` ao carregar a
> sala). Salas/eventos novos exigem o restart (loadNavigator roda no boot).

---

## 2. Modelos bons (sem HC) para salas públicas

`park_a` (praça), `park_b`, `cinema_a` (cinema), `theater` (teatro),
`tearoom` (casa de chá), `rooftop` (rooftop), `pizza` (pizzaria),
`netcafe` (lan house), `pub_a` (pub), `newbie_lobby` (lobby novatos),
`orient` (jardim oriental), `picnic` (parque), `star_lounge` (lounge),
`dusty_lounge`, `model_s` (pequena), `model_a`...`model_n`.

Consulte modelos e tamanho:
```bash
MYSQL_PWD=9911 mysql -h 127.0.0.1 -u habbo habbo \
  -e "SELECT name, door_x, door_y, club_only FROM room_models WHERE club_only='0';"
```

---

## 3. Temas automáticos (decorate-rooms.py)

O decorador escolhe móveis pelo nome da sala (palavra-chave):

| Palavra no nome | Móveis |
|---|---|
| cinema | sofas, poltronas, mesas, TV, lâmpadas, tapete |
| teatro | cadeiras, sofas, lâmpadas, tapete |
| tea / chá | cadeiras, mesa de centro, bonsai |
| rooftop | sofá, mesa, planta, lâmpada, tapete |
| pizza | cadeiras, mesas, geladeira, planta |
| net | sofá, mesa, TV, cadeiras |
| pub | sofá, mesa, cadeiras, lâmpada |
| novato | sofá, mesa, planta, tapete |
| orient | bonsai, mesa baixa, cadeiras, tapete |
| picnic | árvores frutíferas, mesa, cadeiras |
| estrela | sofás, poltrona, mesa, lâmpada |
| praça | árvores, mesa, cadeiras, sofá |

Posicionamento (determinístico por nome): núcleo social com sofás virados pro
centro → mesas de centro → cadeiras ao redor → decoração (plantas/lâmpadas/TV)
nas bordas e cantos. Respeita o heightmap (nunca põe móvel em parede `x`),
`z` = altura do tile, rotações naturais.

Gerar só o SQL (sem criar sala):
```bash
python3 scripts/decorate-rooms.py /tmp/models.json --rooms "64:park_a" --output /tmp/deco.sql
```
(ou rode o fluxo completo do create-themed-room.sh, que já chama o decorador)

---

## 4. Peças soltas (SQL manual)

### Listar salas
```sql
SELECT id, owner_name, name, model, is_public, promoted FROM rooms ORDER BY id;
```

### Criar sala pública (mínimo)
```sql
INSERT INTO rooms (owner_id, owner_name, name, description, model, state, users_max,
  category, is_public, tags) VALUES
(1, 'Systemaccount', 'Minha Sala', 'Descrição', 'model_s', 'open', 25, 1, '1', 'tag1,tag2');
```

### Inserir móvel
```sql
INSERT INTO items (user_id, room_id, item_id, wall_pos, x, y, z, rot, extra_data,
  wired_data, limited_data, guild_id) VALUES
(1, <room_id>, <items_base.id>, '', <x>, <y>, <z>, <rot>, '0', '', '0:0', 0);
```

### Criar evento (promoção)
```sql
INSERT INTO room_promotions (room_id, title, description, end_timestamp,
  start_timestamp, category) VALUES
(<room_id>, 'Título', 'Descrição', UNIX_TIMESTAMP()+604800, UNIX_TIMESTAMP(), 2);
UPDATE rooms SET promoted='1' WHERE id=<room_id>;
```

### Staff Picks
```sql
INSERT INTO navigator_publics (public_cat_id, room_id, visible) VALUES (1, <room_id>, '1');
```

---

## 5. IDs de móveis confirmados (items_base)

| Móvel | ID | Móvel | ID |
|---|---|---|---|
| sofa_polyfon (sofá azul) | 35 | sofa_silo (sofá cinza) | 28 |
| sofachair_polyfon (poltrona) | 34 | chair_polyfon (cadeira) | 18 |
| chair_silo | 26 | chair_norja (cadeira bege) | 30 |
| table_polyfon_med (mesa) | 31 | table_silo_med | 21 |
| table_norja_med | 20 | table_silo_small | 47 |
| bed_polyfon (cama casal) | 41 | bed_trad | 44 |
| carpet_soft (tapete) | 136 | carpet_polar (pele) | 61 |
| plant_cruddy (aloe) | 128 | plant_bonsai | 163 |
| plant_yukka | 165 | plant_big_cactus | 164 |
| plant_fruittree (árvore) | 161 | lamp_basic | 199 |
| shelves_polyfon (estante) | 14 | tv_flat (TV) | 3886 |
| fridge (geladeira) | 201 | | |

---

## 6. Categorias do navigator / eventos

| ID | Categoria pública | ID | Categoria de evento |
|---|---|---|---|
| 1 | Staff Picks | 1 | Hottest Events |
| 2 | Official Games | 2 | Parties & Music |
| 3 | Official Fansites | 3 | Role Play |
| 4 | BAW: Builders at Work | 4 | Help Desk |
| 5 | Room Bundles | 5 | Trading |
| 6 | Safety | 6 | Games |

---

## 7. Detalhes técnicos (por que funciona)

- **Salas públicas** → tab "official-root" do navigator: `rooms.is_public='1'`.
  O emulador carrega no boot (`RoomManager: SELECT * FROM rooms WHERE is_public=1
  OR is_staff_picked=1`).
- **Staff Picks** → `navigator_publics` (cat 1) OU `is_staff_picked='1'`.
- **Eventos** → `room_promotions` com `end_timestamp > now`; aba "categories".
- **Mobília** → `items`; o emulador lê `SELECT * FROM items WHERE room_id=?` ao
  carregar a sala (aparece na 1ª visita, sem restart).
- **Dono**: salas do hotel usam `Systemaccount` (id 1). Móveis com
  `user_id=1` para o dono poder gerenciar (se der direitos).
- O heightmap do mysql vem com `\r\n` escapado — o decorate-rooms.py já trata.

---

## 8. Exemplo completo (já rodado em produção)

12 salas + 6 eventos criados em 2026-09-18 (ids 64-75): Praça Central, Cinema,
Teatro, Casa de Chá, Rooftop, Pizzaria, Net Café, Pub, Lobby Novatos, Jardim
Oriental, Parque Picnic, Estrela Lounge — cada uma decorada com 16 móveis (192
no total). O SQL usado está em `/tmp/crear-salas-eventos.sql` e a decoração
gerada por `scripts/decorate-rooms.py`.

Para criar mais no mesmo padrão:

```bash
sudo bash scripts/create-themed-room.sh "Sala de Jogos" model_s 6 6 "Torneio" "Vem jogar!" 40
sudo systemctl restart habbo-arcturus
```