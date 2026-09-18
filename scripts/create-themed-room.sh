#!/bin/bash
# create-themed-room.sh — Cria sala pública temática + mobília de bom gosto + evento.
#
# Uso:
#   sudo bash create-themed-room.sh <nome_da_sala> <modelo> <categoria_publica> <categoria_evento> "<titulo_evento>" "<descricao_evento>" [max_users]
#
# Exemplo:
#   sudo bash create-themed-room.sh "Sala de Jogos" model_s 6 6 "Torneio de Jogos" "Vem jogar!" 40
#
# Requisitos: mysql client + o script decorate-rooms.py no mesmo diretório.
# OBS: o emulador carrega salas/eventos no boot — rode isto e depois:
#   sudo systemctl restart habbo-arcturus

set -euo pipefail

NAME="${1:?nome da sala}"
MODEL="${2:?modelo (ex: model_s, park_a, cinema_a)}"
PUB_CAT="${3:-1}"
EV_CAT="${4:-2}"
EV_TITLE="${5:-Evento na $NAME}"
EV_DESC="${6:-Venha participar!}"
MAX_USERS="${7:-25}"

MYSQL="mysql -h 127.0.0.1 -u habbo habbo"
export MYSQL_PWD="${MYSQL_PWD:-9911}"

echo "== Criando sala '$NAME' (modelo $MODEL) =="
$MYSQL -e "
INSERT INTO rooms (owner_id, owner_name, name, description, model, password, state,
  users, users_max, guild_id, category, score, paper_floor, paper_wall, paper_landscape,
  thickness_wall, wall_height, thickness_floor, moodlight_data, tags, is_public,
  is_staff_picked, allow_other_pets, allow_other_pets_eat, allow_walkthrough,
  allow_hidewall, chat_mode, chat_weight, chat_speed, chat_hearing_distance,
  chat_protection, override_model, who_can_mute, who_can_kick, who_can_ban,
  poll_id, roller_speed, promoted)
VALUES (1, 'Systemaccount', '$NAME', '$EV_DESC', '$MODEL', '', 'open', 0, $MAX_USERS,
  0, $PUB_CAT, 0, '0.0', '0.0', '0.0', 0, -1, 0,
  '2,1,1,#000000,255;2,3,1,#000000,255;2,3,1,#000000,255;',
  'novo,evento', '1', '0', '0', '0', '1', '0',
  0, 1, 1, 50, 2, '0', 0, 0, 0, 0, 4, '0');
" 

ROOM_ID=$($MYSQL -N -e "SELECT MAX(id) FROM rooms WHERE name='$NAME' AND owner_name='Systemaccount';")
echo "   sala id=$ROOM_ID"

echo "== Decorando com mobília de bom gosto =="
# extrai heightmap do modelo
$MYSQL -N -e "SELECT heightmap FROM room_models WHERE name='$MODEL';" > /tmp/hm_raw.txt
python3 - "$ROOM_ID" "$NAME" <<'PYEOF'
import json, sys, importlib.util
room_id, name = int(sys.argv[1]), sys.argv[2]
spec = importlib.util.spec_from_file_location("dec", "/home/gipsydanger/projects/habbo-dev/scripts/decorate-rooms.py")
dec = importlib.util.module_from_spec(spec); spec.loader.exec_module(dec)
with open("/tmp/hm_raw.txt") as f:
    raw = f.read()
# reparsing (mesmo tratamento do decorate-rooms: linhas com \t = modelo novo)
rows = []
for ln in raw.split("\n"):
    ln = ln.rstrip("\r")
    if not ln: continue
    if "\t" in ln:
        rows = [ln.split("\t", 1)[1]]
    else:
        rows.append(ln)
rows = [r.replace("\\n", "") for r in rows]
tiles = dec.parse_heightmap(rows)
pl = dec.find_placements(tiles, name, count=16)
lines = []
for x, y, furni, rot, z in pl:
    lines.append(f"(1, {room_id}, {dec.FURNI_IDS[furni]}, '', {x}, {y}, {z:.1f}, {rot}, '0', '', '0:0', 0)")
open("/tmp/deco.sql", "w").write(
    "INSERT INTO items (user_id, room_id, item_id, wall_pos, x, y, z, rot, extra_data, wired_data, limited_data, guild_id) VALUES\n"
    + ",\n".join(lines) + ";\n")
print(f"   {len(lines)} moveis gerados")
PYEOF
$MYSQL < /tmp/deco.sql
echo "   mobília inserida"

echo "== Criando evento (promoção de sala, 7 dias) =="
$MYSQL -e "
INSERT INTO room_promotions (room_id, title, description, end_timestamp, start_timestamp, category)
VALUES ($ROOM_ID, '$EV_TITLE', '$EV_DESC', UNIX_TIMESTAMP()+604800, UNIX_TIMESTAMP(), $EV_CAT);
UPDATE rooms SET promoted='1' WHERE id=$ROOM_ID;
INSERT IGNORE INTO navigator_publics (public_cat_id, room_id, visible) VALUES ($PUB_CAT, $ROOM_ID, '1');
"
echo "== PRONTO =="
echo "   Sala: $NAME (id $ROOM_ID)"
echo "   Para aparecer no client, reinicie o emulador:"
echo "   sudo systemctl restart habbo-arcturus"