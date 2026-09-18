#!/usr/bin/env python3
"""
decorate-rooms.py — Gera INSERTs de mobília para salas do Arcturus.

Decora salas com móveis posicionados com bom gosto: lê o heightmap do modelo,
acha tiles andáveis, e posiciona móveis em zonas (entrada, centro, paredes,
cantos) com rotações naturais. Gera SQL de INSERT em items.

Uso:
  python3 decorate-rooms.py <modelos.json> [--rooms "id:nome,..."] [--output x.sql]

Saída: SQL com INSERT INTO items PARA CADA SALA (user_id=1 Systemaccount).
"""
import argparse
import json
import random
import sys

# (item_name, tipo) — tipos: sofa (2x1), cadeira (1x1), mesa (2x1 ou 1x1),
# cama (2x1), tapete (2x2), planta (1x1), decor (1x1)
FURNITURE = [
    # sofas/armchairs
    ("sofa_polyfon", "sofa", 2, 1, 0),      # id 35
    ("sofa_silo", "sofa", 2, 1, 0),         # id 28
    ("sofachair_polyfon", "chair", 1, 1, 0),# id 34
    ("chair_polyfon", "chair", 1, 1, 0),    # id 18
    ("chair_silo", "chair", 1, 1, 0),       # id 26
    ("chair_norja", "chair", 1, 1, 0),      # id 30
    # mesas
    ("table_polyfon_med", "table", 1, 1, 0),# id 31
    ("table_silo_med", "table", 1, 1, 0),   # id 21
    ("table_norja_med", "table", 1, 1, 0),  # id 20
    ("table_silo_small", "table", 1, 1, 0), # id 47
    # camas
    ("bed_polyfon", "bed", 2, 1, 0),        # id 41
    ("bed_trad", "bed", 2, 1, 0),           # id 44
    # tapetes
    ("carpet_soft", "rug", 2, 2, 0),        # id 136
    ("carpet_polar", "rug", 2, 2, 0),       # id 61
    # plantas/decoração
    ("plant_cruddy", "plant", 1, 1, 0),     # id 128
    ("plant_bonsai", "plant", 1, 1, 0),     # id 163
    ("plant_yukka", "plant", 1, 1, 0),      # id 165
    ("plant_big_cactus", "plant", 1, 1, 0), # id 164
    ("plant_fruittree", "plant", 1, 1, 0),  # id 161
    ("lamp_basic", "lamp", 1, 1, 0),        # id 199
    ("shelves_polyfon", "shelf", 1, 1, 0),  # id 14
    ("tv_flat", "tv", 1, 1, 4),             # id 3886
    ("fridge", "fridge", 1, 1, 0),          # id 201
]

# Mapa furni -> items_base.id (confirmado no banco)
FURNI_IDS = {
    "sofa_polyfon": 35, "sofa_silo": 28, "sofachair_polyfon": 34,
    "chair_polyfon": 18, "chair_silo": 26, "chair_norja": 30,
    "table_polyfon_med": 31, "table_silo_med": 21, "table_norja_med": 20,
    "table_silo_small": 47,
    "bed_polyfon": 41, "bed_trad": 44,
    "carpet_soft": 136, "carpet_polar": 61,
    "plant_cruddy": 128, "plant_bonsai": 163, "plant_yukka": 165,
    "plant_big_cactus": 164, "plant_fruittree": 161,
    "lamp_basic": 199, "shelves_polyfon": 14, "tv_flat": 3886, "fridge": 201,
}

# Paletas por tema de sala: nome da sala contém palavra -> lista de furnis
THEMES = {
    "cinema": ["sofa_polyfon", "chair_polyfon", "table_polyfon_med", "tv_flat", "lamp_basic", "carpet_soft"],
    "teatro": ["chair_norja", "chair_polyfon", "sofa_silo", "lamp_basic", "carpet_polar"],
    "tea": ["chair_silo", "table_silo_med", "plant_bonsai", "table_silo_small", "carpet_soft"],
    "rooftop": ["sofa_silo", "table_silo_med", "plant_yukka", "lamp_basic", "carpet_polar"],
    "pizza": ["chair_polyfon", "table_polyfon_med", "fridge", "plant_cruddy", "lamp_basic"],
    "net": ["sofa_polyfon", "table_norja_med", "tv_flat", "chair_silo", "lamp_basic"],
    "pub": ["sofa_silo", "table_silo_med", "chair_norja", "lamp_basic", "carpet_soft"],
    "novato": ["sofa_polyfon", "table_polyfon_med", "plant_cruddy", "carpet_soft", "lamp_basic"],
    "orient": ["plant_bonsai", "table_silo_small", "chair_silo", "carpet_polar", "lamp_basic"],
    "picnic": ["plant_fruittree", "table_norja_med", "chair_polyfon", "carpet_soft", "plant_yukka"],
    "estrela": ["sofa_polyfon", "sofachair_polyfon", "table_polyfon_med", "lamp_basic", "carpet_polar"],
    "praça": ["plant_fruittree", "plant_yukka", "table_norja_med", "chair_polyfon", "sofa_silo"],
}

def parse_heightmap(rows):
    """Retorna dict (x,y) -> altura (float) para tiles andáveis."""
    tiles = {}
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c.lower() != "x":
                # altura: dígito ou letra (a=10,...)
                if c.isdigit():
                    tiles[(x, y)] = float(c)
                else:
                    tiles[(x, y)] = float(ord(c.lower()) - ord("a") + 10)
    return tiles

def pick_theme(name):
    for key, furnis in THEMES.items():
        if key in name.lower():
            return furnis
    return ["sofa_polyfon", "table_polyfon_med", "chair_polyfon", "plant_cruddy", "lamp_basic"]

def find_placements(tiles, room_name, count=18):
    """Distribui móveis com bom senso: centro (conversa), paredes (decoração), cantos."""
    xs = [p[0] for p in tiles]
    ys = [p[1] for p in tiles]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2

    # ordena tiles por distância ao centro (zona social) depois anel externo
    center_tiles = sorted(tiles, key=lambda p: abs(p[0] - cx) + abs(p[1] - cy))
    edge_tiles = sorted(tiles, key=lambda p: -abs(p[0] - cx) - abs(p[1] - cy))

    placements = []
    used = set()

    def claim(x, y, w=1, h=1):
        for dx in range(w):
            for dy in range(h):
                if (x + dx, y + dy) in used or (x + dx, y + dy) not in tiles:
                    return False
        for dx in range(w):
            for dy in range(h):
                used.add((x + dx, y + dy))
        return True

    theme = pick_theme(room_name)
    random.seed(room_name)  # determinístico por sala

    # 1) núcleo: 1-2 sofas/centerpiece virados pro centro
    for i, (x, y) in enumerate(center_tiles):
        if len(placements) >= 5:
            break
        if claim(x, y, 2, 1):
            furni = theme[0]
            rot = 2 if y < cy else 0 if y > cy else 4
            placements.append((x, y, furni, rot))
    # 2) mesas de centro
    for (x, y) in center_tiles:
        if len(placements) >= 8:
            break
        if claim(x, y, 1, 1):
            furni = theme[1]
            placements.append((x, y, furni, 0))
    # 3) cadeiras em volta do centro
    for (x, y) in center_tiles:
        if len(placements) >= 13:
            break
        if claim(x, y, 1, 1):
            furni = theme[2]
            placements.append((x, y, furni, random.choice([0, 2, 4, 6])))
    # 4) decoração nas bordas (plantas, lâmpadas, tv, estante)
    deco = [f for f in theme if f not in theme[:3]]
    for (x, y) in edge_tiles:
        if len(placements) >= count:
            break
        if claim(x, y, 1, 1):
            furni = deco[(len(placements)) % len(deco)]
            rot = random.choice([0, 2, 4, 6]) if furni not in ("tv_flat",) else 4
            placements.append((x, y, furni, rot))

    return [(x, y, furni, rot, tiles[(x, y)]) for x, y, furni, rot in placements]

def generate(room_id, room_name, rows, owner_id=1):
    tiles = parse_heightmap(rows)
    placements = find_placements(tiles, room_name)
    lines = []
    for x, y, furni, rot, z in placements:
        base_id = FURNI_IDS[furni]
        extra = "0"  # móvel comum
        lines.append(
            f"({owner_id}, {room_id}, {base_id}, '', {x}, {y}, {z:.1f}, {rot}, '{extra}', '', '0:0', 0)"
        )
    return lines

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models_json")
    ap.add_argument("--rooms", default="", help="id:nome,id:nome (default: todos)")
    ap.add_argument("--output", default="/tmp/decorate-rooms.sql")
    args = ap.parse_args()

    models = json.load(open(args.models_json))
    if args.rooms:
        wanted = dict(tuple(p.split(":")) for p in args.rooms.split(",") if ":" in p)
    else:
        wanted = {}

    all_lines = []
    for name, rows in models.items():
        if wanted and name not in wanted:
            continue
        room_id = wanted.get(name, "ID")
        # coloca o room id real (deve ser passado) — fallback: nome = id não resolve
        all_lines.extend(generate(room_id, name, rows))

    with open(args.output, "w") as f:
        f.write("INSERT INTO items (user_id, room_id, item_id, wall_pos, x, y, z, rot, extra_data, wired_data, limited_data, guild_id) VALUES\n")
        f.write(",\n".join(all_lines))
        f.write(";\n")
    print(f"Gerados {len(all_lines)} móveis -> {args.output}")

if __name__ == "__main__":
    main()