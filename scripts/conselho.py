#!/usr/bin/env python3
"""
conselho.py — Conselho Arquitetônico do Atom Hotel.

Um "curador estético" que avalia salas por critérios de beleza, estilo e
funcionalidade, e só APROVA salas que passarem em todos os requisitos.
Emite parecer detalhado com nota (0-10) e lista de reprovações.

Critérios (cada um é um "conselheiro"):
  1. Ocupação  — densidade de móveis vs área andável (nem depósito, nem vazio)
  2. Circulação — sobra caminho livre (sem bloquear a porta / miolo)
  3. Zonas      — a sala tem um núcleo social claro (assentos agrupados)
  4. Estilo     — coerência de família (1 família dominante + acentos)
  5. Borda      — decoração nas paredes/cantos (plantas, lâmpadas, TV)
  6. Obstrução  — móveis não se sobrepõem (itens empilhados no mesmo tile)
  7. Assentos   — há assentos suficientes para o tamanho da sala
  8. Mesa       — assentos têm mesa de apoio por perto

Uso:
  python3 conselho.py <room_id> [--json]        avalia UMA sala
  python3 conselho.py --todas                   avalia todas as salas públicas
"""
import argparse
import json
import os
import subprocess
import sys

MYSQL_PWD = os.environ.get("MYSQL_PWD", "9911")

# Famílias de estilo (item_name -> família) — baseado no catálogo real
FAMILIES = {
    "sofa_polyfon": "polyfon", "sofachair_polyfon": "polyfon", "chair_polyfon": "polyfon",
    "table_polyfon_med": "polyfon", "bed_polyfon": "polyfon", "shelves_polyfon": "polyfon",
    "sofa_silo": "silo", "chair_silo": "silo", "table_silo_med": "silo", "table_silo_small": "silo",
    "chair_norja": "norja", "table_norja_med": "norja",
    "plant_cruddy": "planta", "plant_bonsai": "planta", "plant_yukka": "planta",
    "plant_big_cactus": "planta", "plant_fruittree": "planta",
    "lamp_basic": "lamp", "tv_flat": "tv", "fridge": "fridge",
    "carpet_soft": "tapete", "carpet_polar": "tapete",
    "table_silo_small*1": "silo",
}

# Função do item para julgamento
def item_role(item_name):
    if "sofa" in item_name or "sofachair" in item_name:
        return "sofa"
    if "chair" in item_name:
        return "chair"
    if "table" in item_name:
        return "table"
    if "bed" in item_name:
        return "bed"
    if "carpet" in item_name:
        return "carpet"
    if "lamp" in item_name:
        return "lamp"
    if "plant" in item_name or "tree" in item_name:
        return "plant"
    if "tv" in item_name:
        return "tv"
    if "shelves" in item_name:
        return "shelf"
    if "fridge" in item_name:
        return "fridge"
    return "decor"


def db(sql, db="habbo"):
    env = dict(os.environ)
    env["MYSQL_PWD"] = MYSQL_PWD
    p = subprocess.run(["mysql", "-h", "127.0.0.1", "-u", "habbo", db, "-N", "-e", sql],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip()[:300])
    return p.stdout


def load_room(room_id):
    """Carrega sala + móveis do banco."""
    room = db(f"SELECT id, name, model, users_max, is_public FROM rooms WHERE id={room_id};")
    if not room:
        raise SystemExit(f"sala {room_id} não existe")
    rid, rname, model_name, users_max, is_public = room.split("\t")

    # altura do modelo (heightmap) p/ área andável
    hm = db(f"SELECT heightmap FROM room_models WHERE name='{model_name}';")
    if not hm:
        raise SystemExit(f"modelo {model_name} não encontrado")
    rows = hm.replace("\\r\\n", "\n").replace("\r\n", "\n").strip("\n").split("\n")
    walkable = 0
    for row in rows:
        walkable += sum(1 for c in row if c not in "xX ")

    # móveis
    items = []
    for line in db(f"SELECT i.id, i.x, i.y, i.z, i.rot, b.item_name, b.width, b.length, "
                   f"b.allow_sit, b.allow_lay, b.allow_stack, b.stack_height "
                   f"FROM items i JOIN items_base b ON b.id=i.item_id "
                   f"WHERE i.room_id={room_id} ORDER BY i.id;").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        items.append({
            "id": int(parts[0]), "x": int(parts[1]), "y": int(parts[2]),
            "z": float(parts[3]), "rot": int(parts[4]), "name": parts[5],
            "w": int(parts[6]), "l": int(parts[7]), "sit": parts[8] == "1",
            "lay": parts[9] == "1", "stack": parts[10] == "1",
            "stack_h": float(parts[11]),
        })

    return {"id": rid, "name": rname, "model": model_name, "users_max": int(users_max),
            "walkable": walkable, "items": items, "rows": rows}


def occupied_tiles(items):
    """Mapeia (x,y) -> lista de itens que ocupam (considerando w/l + rot)."""
    occ = {}
    for it in items:
        w, l = it["w"], it["l"]
        if it["rot"] % 2 == 1:
            w, l = l, w
        for dx in range(w):
            for dy in range(l):
                occ.setdefault((it["x"] + dx, it["y"] + dy), []).append(it)
    return occ


def consegue_avaliar(room):
    """O conselho emite parecer; retorna (aprovado: bool, nota: float, parecer: list[str])."""
    items = room["items"]
    area = room["walkable"]
    occ = occupied_tiles(items)
    verdicts = []
    reasons = []

    # ---- 1. OCUPAÇÃO ----
    n = len(items)
    density = n / max(area, 1)
    if n < 3:
        reasons.append(f"1·OCUPAÇÃO reprovada: só {n} móveis (sala parece vazia)")
        occ_ok = False
    elif density > 0.15:
        reasons.append(f"1·OCUPAÇÃO reprovada: {n} móveis em {area} tiles = depósito (máx {area*0.15:.0f})")
        occ_ok = False
    else:
        occ_ok = True
        verdicts.append(f"OCUPAÇÃO ok: {n} móveis em {area} tiles (densidade {density:.2%}, limite 15%)")

    # ---- 2. CIRCULAÇÃO (porta livre + miolo) ----
    # acha a porta (canto do heightmap com piso)
    rows = room["rows"]
    door = None
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c not in "xX ":
                door = (x, y)
                break
        if door:
            break
    door_blocked = False
    if door:
        for dx in range(3):
            for dy in range(3):
                if occ.get((door[0] + dx - 1, door[1] + dy - 1)):
                    door_blocked = True
    if door_blocked:
        reasons.append("2·CIRCULAÇÃO reprovada: móvel bloqueia a entrada")
        circ_ok = False
    else:
        circ_ok = True
        verdicts.append("CIRCULAÇÃO ok: entrada livre")

    # ---- 3. ZONA SOCIAL (assentos agrupados) ----
    seats = [it for it in items if it["sit"]]
    # agrupa por proximidade (dist <= 3 tiles)
    groups = []
    for s in seats:
        placed = False
        for g in groups:
            if any(abs(s["x"] - o["x"]) <= 3 and abs(s["y"] - o["y"]) <= 3 for o in g):
                g.append(s)
                placed = True
                break
        if not placed:
            groups.append([s])
    biggest = max((len(g) for g in groups), default=0)
    if biggest >= 3:
        verdicts.append(f"ZONA SOCIAL ok: {len(seats)} assentos, maior grupo {biggest}")
        zone_ok = True
    else:
        reasons.append(f"3·ZONA SOCIAL reprovada: assentos espalhados (maior grupo {biggest}, precisa ≥3)")
        zone_ok = False

    # ---- 4. ESTILO (família dominante) ----
    fam_count = {}
    for it in items:
        fam = FAMILIES.get(it["name"], "outro")
        fam_count[fam] = fam_count.get(fam, 0) + 1
    if not fam_count:
        style_ok = False
        reasons.append("4·ESTILO reprovada: sem móveis para avaliar")
    else:
        top_fam, top_n = max(fam_count.items(), key=lambda kv: kv[1])
        total = sum(fam_count.values())
        if top_n / total >= 0.4:
            verdicts.append(f"ESTILO ok: família dominante '{top_fam}' ({top_n}/{total})")
            style_ok = True
        else:
            reasons.append(f"4·ESTILO reprovada: sem família dominante ({fam_count})")
            style_ok = False

    # ---- 5. BORDA/DECORAÇÃO (plantas/lâmpadas/TV) ----
    decor = sum(1 for it in items if item_role(it["name"]) in ("plant", "lamp", "tv", "shelf"))
    if decor >= 3:
        verdicts.append(f"DECORAÇÃO ok: {decor} peças de ambientação")
        decor_ok = True
    else:
        reasons.append(f"5·DECORAÇÃO reprovada: só {decor} peças de ambientação (min 3)")
        decor_ok = False

    # ---- 6. OBSTRUÇÃO (sobreposição) ----
    overlaps = 0
    for tiles, its in occ.items():
        if len(its) > 1:
            # tapete debaixo de móvel é OK (stack_height baixo)
            non_carpet = [it for it in its if item_role(it["name"]) != "carpet"]
            if len(non_carpet) > 1:
                overlaps += 1
    if overlaps == 0:
        verdicts.append("OBSTRUÇÃO ok: nenhum móvel sobreposto")
        obs_ok = True
    else:
        reasons.append(f"6·OBSTRUÇÃO reprovada: {overlaps} tiles com móveis sobrepostos")
        obs_ok = False

    # ---- 7. ASSENTOS ----
    seat_min = max(2, min(room["users_max"] // 4, 10))
    if len(seats) >= seat_min:
        verdicts.append(f"ASSENTOS ok: {len(seats)} (mín {seat_min} p/ {room['users_max']} usuários)")
        seat_ok = True
    else:
        reasons.append(f"7·ASSENTOS reprovada: {len(seats)} assentos < mín {seat_min}")
        seat_ok = False

    # ---- 8. MESA perto de assentos ----
    tables = [it for it in items if item_role(it["name"]) == "table"]
    tables_near = 0
    for s in seats[:6]:
        if any(abs(s["x"] - t["x"]) <= 2 and abs(s["y"] - t["y"]) <= 2 for t in tables):
            tables_near += 1
    if seats and tables_near / len(seats[:6]) >= 0.5:
        verdicts.append(f"MESA ok: {tables_near}/{min(len(seats),6)} assentos com mesa por perto")
        table_ok = True
    else:
        reasons.append(f"8·MESA reprovada: só {tables_near} assentos com mesa de apoio")
        table_ok = False

    checks = [occ_ok, circ_ok, zone_ok, style_ok, decor_ok, obs_ok, seat_ok, table_ok]
    nota = round(sum(checks) / len(checks) * 10, 1)
    aprovado = all(checks)

    return aprovado, nota, verdicts, reasons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("room_id", nargs="?", help="id da sala (ou --todas)")
    ap.add_argument("--todas", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.todas:
        salas = [l.split("\t")[0] for l in db("SELECT id FROM rooms WHERE is_public='1' ORDER BY id;").splitlines() if l.strip()]
    elif args.room_id:
        salas = [args.room_id]
    else:
        ap.error("passe <room_id> ou --todas")

    resultados = []
    for rid in salas:
        room = load_room(rid)
        aprovado, nota, verdicts, reasons = consegue_avaliar(room)
        status = "APROVADA" if aprovado else "REPROVADA"
        if args.json:
            resultados.append({"room_id": int(rid), "nome": room["name"], "aprovada": aprovado,
                               "nota": nota, "móveis": len(room["items"]), "motivos": reasons})
        else:
            print("=" * 60)
            print(f"[{status}] Sala {rid} — {room['name']} (modelo {room['model']}, {len(room['items'])} móveis)")
            print(f"Nota: {nota}/10")
            for v in verdicts:
                print(f"  ✓ {v}")
            for r in reasons:
                print(f"  ✗ {r}")
    if args.json:
        print(json.dumps(resultados, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()