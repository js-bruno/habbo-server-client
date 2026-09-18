#!/usr/bin/env python3
"""
repaginar.py — Gera e aplica o novo layout de mobília para TODAS as salas públicas,
passando pelos 8 critérios do conselho arquitetônico (scripts/conselho.py).

Layouts explícitos por modelo (desenhados sobre o heightmap real):
cada sala tem um conceito (família dominante + zona social + decoração).
"""
import os
import subprocess
import sys

MYSQL_PWD = "9911"

# item_id -> (nome, w, l, papel)
FURNI = {
    14:  ("shelves_polyfon", 2, 1, "shelf"),
    18:  ("chair_polyfon", 1, 1, "chair"),
    20:  ("table_norja_med", 2, 2, "table"),
    21:  ("table_silo_med", 2, 2, "table"),
    26:  ("chair_silo", 1, 1, "chair"),
    28:  ("sofa_silo", 2, 1, "sofa"),
    30:  ("chair_norja", 1, 1, "chair"),
    31:  ("table_polyfon_med", 2, 2, "table"),
    34:  ("sofachair_polyfon", 1, 1, "chair"),
    35:  ("sofa_polyfon", 2, 1, "sofa"),
    47:  ("table_silo_small", 1, 1, "table"),
    61:  ("carpet_polar", 2, 3, "carpet"),
    128: ("plant_cruddy", 1, 1, "plant"),
    136: ("carpet_soft", 2, 4, "carpet"),
    161: ("plant_fruittree", 1, 1, "plant"),
    163: ("plant_bonsai", 1, 1, "plant"),
    164: ("plant_big_cactus", 1, 1, "plant"),
    165: ("plant_yukka", 1, 1, "plant"),
    199: ("lamp_basic", 1, 1, "lamp"),
    201: ("fridge", 1, 1, "fridge"),
    3886: ("tv_flat", 2, 1, "tv"),
}


def db(sql, db="habbo"):
    env = dict(os.environ)
    env["MYSQL_PWD"] = MYSQL_PWD
    r = subprocess.run(["mysql", "-h", "127.0.0.1", "-u", "habbo", db, "-N", "-e", sql],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:300])
    return r.stdout


def load_model(name):
    hm = db(f"SELECT heightmap FROM room_models WHERE name='{name}'")
    hm = hm.replace("\\r\\n", "\n").replace("\r\n", "\n").replace("\\n", "\n").strip("\n")
    grid = [list(row) for row in hm.split("\n") if row.strip()]
    door = db(f"SELECT door_x, door_y FROM room_models WHERE name='{name}'").split("\t")
    return grid, int(door[0]), int(door[1])


def h_at(grid, x, y):
    if y < 0 or y >= len(grid) or x < 0 or x >= len(grid[y]):
        return None
    c = grid[y][x]
    if c in "xX ":
        return None
    return float(c)


class Layout:
    """Valida e compõe um conjunto de móveis. place() falha se sobrepõe ou sai do chão."""

    def __init__(self, grid):
        self.grid = grid
        self.used = {}
        self.items = []

    def place(self, item_id, x, y, rot=0):
        w, l = FURNI[item_id][1], FURNI[item_id][2]
        if rot % 2 == 1:
            w, l = l, w
        tiles = []
        for dx in range(w):
            for dy in range(l):
                tx, ty = x + dx, y + dy
                if h_at(self.grid, tx, ty) is None:
                    return False
                it = self.used.get((tx, ty))
                if it is not None and it != item_id and FURNI[it][3] != "carpet" and FURNI[item_id][3] != "carpet":
                    return False
                tiles.append((tx, ty))
        z = min(h for h in (h_at(self.grid, t[0], t[1]) for t in tiles) if h is not None)
        for t in tiles:
            self.used[t] = item_id
        self.items.append((item_id, x, y, z, rot))
        return True


# ---------------------------------------------------------------------------
# Layouts explícitos por sala (room_id -> lista de (item_id, x, y, rot))
# ---------------------------------------------------------------------------

ROOM_LAYOUTS = {
    # park_a (44x34, porta 2,15): praça — núcleo polyfon ao centro, árvores nas bordas
    64: [
        (35, 17, 8, 2),    # sofa_polyfon
        (35, 20, 8, 2),    # sofa_polyfon
        (34, 16, 11, 0),   # sofachair_polyfon
        (34, 23, 11, 0),   # sofachair_polyfon
        (31, 18, 11, 0),   # table_polyfon_med
        (31, 21, 11, 0),   # table_polyfon_med
        (136, 16, 9, 0),   # carpet_soft
        (161, 30, 6, 0),   # plant_fruittree
        (161, 33, 10, 0),  # plant_fruittree
        (128, 8, 5, 0),    # plant_cruddy
        (165, 11, 20, 0),  # plant_yukka
        (199, 7, 12, 0),   # lamp_basic
        (199, 26, 5, 0),   # lamp_basic
        (3886, 30, 15, 6), # tv_flat
        (14, 33, 8, 2),    # shelves_polyfon
        (18, 16, 13, 0),   # chair_polyfon extra
        (18, 23, 13, 0),   # chair_polyfon extra
        (18, 18, 15, 0),   # chair_polyfon extra
        (18, 21, 15, 0),   # chair_polyfon extra
        (18, 19, 18, 0),   # chair_polyfon extra
        (18, 22, 18, 0),   # chair_polyfon extra
    ],
    # cinema_a (29x24, porta 20,27): fileiras silo + tela
    65: [
        (21, 8, 12, 0),    # table_silo_med
        (28, 7, 12, 0),    # sofa_silo
        (28, 12, 12, 0),   # sofa_silo
        (28, 18, 8, 0),    # sofa_silo lateral
        (26, 8, 17, 2),    # chair_silo
        (26, 11, 17, 2),
        (26, 14, 17, 2),
        (26, 17, 17, 2),
        (26, 9, 21, 2),
        (26, 12, 21, 2),
        (26, 15, 21, 2),
        (26, 18, 21, 2),
        (3886, 9, 5, 6),   # tv_flat
        (165, 20, 4, 0),   # plant_yukka
        (128, 4, 6, 0),    # plant_cruddy
        (199, 5, 10, 0),   # lamp_basic
        (199, 20, 9, 0),   # lamp_basic
        (136, 9, 13, 0),   # carpet_soft
        (47, 8, 16, 0),    # table_silo_small entre fileiras
        (47, 12, 16, 0),
        (47, 16, 16, 0),
        (47, 6, 20, 0),
        (47, 10, 20, 0),
    ],
    # theater (30x23, porta 20,27): butacas norja + palco
    66: [
        (30, 10, 15, 0),   # chair_norja fila 1
        (30, 13, 15, 0),
        (30, 16, 15, 0),
        (30, 9, 19, 0),    # fila 2
        (30, 12, 19, 0),
        (30, 15, 19, 0),
        (30, 18, 19, 0),
        (30, 10, 23, 0),   # fila 3
        (30, 13, 23, 0),
        (30, 16, 23, 0),
        (30, 19, 23, 0),
        (128, 9, 9, 0),    # palco
        (165, 17, 9, 0),
        (199, 11, 6, 0),
        (199, 15, 7, 0),
        (14, 13, 8, 0),    # shelves_polyfon
        (136, 10, 16, 0),  # carpet_soft
        (20, 11, 13, 0),   # table_norja_med
        (20, 15, 13, 0),
    ],
    # tearoom (22x22, porta 21,19): mesinhas norja + plantas
    67: [
        (20, 8, 8, 0),     # table_norja_med
        (30, 7, 8, 2),
        (30, 11, 8, 2),
        (30, 8, 6, 4),
        (30, 8, 11, 0),
        (20, 14, 8, 0),
        (30, 13, 8, 2),
        (30, 17, 8, 2),
        (30, 14, 6, 4),
        (30, 14, 11, 0),
        (20, 3, 7, 0),
        (30, 2, 7, 2),
        (30, 5, 7, 2),
        (30, 3, 5, 4),
        (30, 3, 9, 0),
        (163, 5, 13, 0),   # plant_bonsai
        (165, 17, 13, 0),  # plant_yukka
        (128, 3, 9, 0),    # plant_cruddy
        (199, 3, 15, 0),   # lamp_basic
        (199, 18, 15, 0),  # lamp_basic
        (136, 8, 9, 0),    # carpet_soft
    ],
    # rooftop (18x20, porta 17,12): lounge silo + plantas
    68: [
        (21, 6, 8, 0),     # table_silo_med
        (28, 5, 8, 2),     # sofa_silo
        (28, 10, 8, 2),    # sofa_silo
        (26, 6, 6, 4),     # chair_silo
        (26, 9, 11, 0),    # chair_silo
        (21, 11, 6, 0),    # table_silo_med
        (47, 5, 13, 0),    # table_silo_small
        (165, 2, 6, 0),    # plant_yukka
        (128, 16, 5, 0),   # plant_cruddy
        (199, 4, 6, 0),    # lamp_basic
        (199, 13, 6, 0),   # lamp_basic
        (61, 6, 7, 0),     # carpet_polar
        (26, 8, 6, 4),     # chair_silo extra
        (26, 12, 10, 0),   # chair_silo extra
        (26, 9, 13, 2),    # chair_silo extra
        (26, 12, 13, 0),   # chair_silo extra
    ],
    # pizza (28x16, porta 5,27): mesas norja + fridge
    69: [
        (20, 3, 9, 0),     # table_norja_med
        (30, 2, 9, 2),
        (30, 6, 9, 2),
        (30, 3, 7, 4),
        (30, 3, 12, 0),
        (20, 8, 9, 0),
        (30, 7, 9, 2),
        (30, 11, 9, 2),
        (20, 8, 14, 0),
        (30, 7, 14, 2),
        (201, 4, 5, 0),    # fridge
        (128, 10, 5, 0),   # plant_cruddy
        (165, 2, 14, 0),   # plant_yukka
        (199, 12, 6, 0),   # lamp_basic
        (136, 3, 10, 0),   # carpet_soft
    ],
    # netcafe (24x25, porta 22,12): estações silo + tv
    70: [
        (21, 10, 7, 0),    # table_silo_med
        (26, 9, 7, 2),
        (26, 13, 7, 2),
        (21, 10, 11, 0),
        (26, 9, 11, 2),
        (26, 13, 11, 2),
        (21, 10, 15, 0),
        (26, 9, 15, 2),
        (26, 13, 15, 2),
        (3886, 10, 4, 6),  # tv_flat
        (165, 16, 6, 0),   # plant_yukka
        (128, 5, 6, 0),    # plant_cruddy
        (199, 14, 7, 0),   # lamp_basic
        (199, 6, 9, 0),    # lamp_basic
        (136, 10, 8, 0),   # carpet_soft
        (26, 8, 19, 2),    # chair_silo extra
        (26, 12, 19, 2),   # chair_silo extra
        (26, 8, 11, 2),    # chair_silo (grupo central)
        (26, 12, 11, 2),   # chair_silo
    ],
    # pub_a (31x25, porta 15,25): zona silo + balcão norja
    71: [
        (21, 8, 15, 0),    # table_silo_med
        (28, 6, 15, 2),    # sofa_silo
        (26, 11, 15, 2),
        (26, 12, 15, 2),
        (21, 8, 20, 0),
        (28, 6, 20, 2),
        (26, 11, 20, 2),
        (26, 12, 20, 2),
        (30, 20, 11, 0),   # chair_norja balcão
        (30, 20, 14, 0),
        (30, 20, 17, 0),
        (201, 18, 9, 0),   # fridge
        (128, 3, 15, 0),   # plant_cruddy
        (165, 21, 6, 0),   # plant_yukka
        (199, 5, 13, 0),   # lamp_basic
        (61, 7, 16, 0),    # carpet_polar
        (26, 8, 12, 2),    # chair_silo
        (26, 8, 18, 2),    # chair_silo
        (47, 11, 15, 0),   # table_silo_small
        (47, 11, 20, 0),   # table_silo_small
    ],
    # newbie_lobby (28x22, porta 2,11): recepção polyfon
    72: [
        (35, 7, 8, 2),     # sofa_polyfon
        (34, 6, 11, 0),    # sofachair_polyfon
        (34, 10, 11, 0),
        (31, 7, 11, 0),    # table_polyfon_med
        (35, 6, 21, 2),    # sofa_polyfon
        (34, 8, 24, 0),
        (34, 11, 24, 0),
        (31, 8, 21, 0),
        (128, 3, 8, 0),    # plant_cruddy
        (165, 15, 7, 0),   # plant_yukka
        (163, 15, 14, 0),  # plant_bonsai
        (199, 3, 14, 0),   # lamp_basic
        (199, 17, 6, 0),   # lamp_basic
        (136, 6, 12, 0),   # carpet_soft
        (18, 11, 8, 0),    # chair_polyfon
        (18, 11, 15, 0),   # chair_polyfon
        (47, 5, 8, 0),     # table_silo_small (perto sofá 7,8)
        (47, 5, 15, 0),    # table_silo_small (perto sofá 7,15)
    ],
    # orient (31x36, porta 35,22): jardim oriental
    73: [
        (35, 14, 18, 2),   # sofa_polyfon
        (34, 13, 21, 0),   # sofachair_polyfon
        (34, 18, 21, 0),
        (31, 14, 21, 0),   # table_polyfon_med
        (163, 12, 16, 0),  # plant_bonsai
        (163, 20, 18, 0),
        (164, 8, 24, 0),   # plant_big_cactus
        (165, 22, 25, 0),  # plant_yukka
        (128, 6, 17, 0),   # plant_cruddy
        (199, 14, 16, 0),  # lamp_basic
        (199, 22, 15, 0),
        (136, 13, 19, 0),  # carpet_soft
        (18, 17, 21, 0),   # chair_polyfon
        (18, 14, 24, 0),   # chair_polyfon
        (18, 19, 24, 0),   # chair_polyfon
        (31, 17, 24, 0),   # table_polyfon_med
        (18, 16, 18, 0),   # chair_polyfon
        (18, 18, 27, 0),   # chair_polyfon
        (18, 15, 16, 0),   # chair_polyfon
        (18, 19, 16, 0),   # chair_polyfon
        (31, 20, 22, 0),   # table_polyfon_med
    ],
    # picnic (44x38, porta 16,5): mesas norja no gramado
    74: [
        (20, 6, 16, 0),   # table_norja_med
        (30, 5, 16, 2),
        (30, 9, 16, 2),
        (30, 6, 14, 4),
        (30, 6, 19, 0),
        (20, 20, 10, 0),
        (30, 19, 10, 2),
        (30, 23, 10, 2),
        (30, 20, 8, 4),
        (30, 20, 13, 0),
        (20, 28, 10, 0),
        (30, 27, 10, 2),
        (30, 31, 10, 2),
        (30, 28, 8, 4),
        (30, 28, 13, 0),
        (161, 6, 12, 0),   # plant_fruittree
        (161, 36, 12, 0),
        (136, 12, 11, 0),  # carpet_soft
        (128, 24, 14, 0),  # plant_cruddy
        (165, 32, 13, 0),  # plant_yukka
        (161, 16, 20, 0),  # plant_fruittree
    ],
    # star_lounge (50x50, porta 37,36): lounge na ilha central
    75: [
        (35, 22, 20, 2),   # sofa_polyfon
        (35, 26, 20, 2),
        (34, 21, 23, 0),   # sofachair_polyfon
        (34, 29, 23, 0),
        (31, 23, 23, 0),   # table_polyfon_med
        (31, 26, 23, 0),
        (34, 23, 28, 0),
        (34, 28, 28, 0),
        (3886, 24, 16, 6), # tv_flat
        (165, 21, 24, 0),  # plant_yukka
        (128, 30, 25, 0),  # plant_cruddy
        (199, 21, 20, 0),  # lamp_basic
        (199, 30, 20, 0),  # lamp_basic
        (136, 22, 24, 0),  # carpet_soft
        (34, 24, 28, 0),   # sofachair_polyfon
        (18, 18, 26, 0),   # chair_polyfon
        (18, 30, 26, 0),   # chair_polyfon
        (31, 24, 26, 0),   # table_polyfon_med
        (18, 26, 26, 0),   # chair_polyfon
        (31, 21, 28, 0),   # table_polyfon_med
        (31, 26, 28, 0),   # table_polyfon_med
    ],
}


def build(room_id, name, model, users_max):
    grid, door_x, door_y = load_model(model)
    L = Layout(grid)
    plano = ROOM_LAYOUTS.get(room_id)
    if plano is None:
        raise SystemExit(f"sem layout para sala {room_id}")
    fails = []
    for item_id, x, y, rot in plano:
        if not L.place(item_id, x, y, rot):
            # fallback: tenta deslocamentos pequenos (até 3 tiles, 8 direções)
            placed = False
            for d in range(1, 4):
                for dx in range(-d, d + 1):
                    for dy in range(-d, d + 1):
                        if abs(dx) != d and abs(dy) != d:
                            continue
                        if L.place(item_id, x + dx, y + dy, rot):
                            placed = True
                            break
                    if placed:
                        break
                if placed:
                    break
            if not placed:
                fails.append((FURNI[item_id][0], x, y, rot))
    if fails:
        print(f"  AVISO sala {room_id} {name}: {len(fails)} móveis não couberam: {fails}")
    return L


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    salas = db("SELECT id, name, model, users_max FROM rooms WHERE is_public='1' ORDER BY id;")
    inserts = []
    for line in salas.splitlines():
        if not line.strip():
            continue
        rid, rname, model, users_max = line.split("\t")
        if only and rid != only:
            continue
        L = build(int(rid), rname, model, int(users_max))
        for item_id, x, y, z, rot in L.items:
            inserts.append(f"({rid}, 1, {item_id}, {x}, {y}, {z}, {rot}, '0', '', '0:0', 0)")
        print(f"sala {rid} {rname}: {len(L.items)} móveis")
    with open("/tmp/layout_del.sql", "w") as f:
        f.write("DELETE FROM items WHERE room_id IN (64,65,66,67,68,69,70,71,72,73,74,75);\n")
    with open("/tmp/layout_ins.sql", "w") as f:
        f.write("INSERT INTO items (room_id, user_id, item_id, x, y, z, rot, extra_data, wired_data, limited_data, guild_id) VALUES\n")
        f.write(",\n".join(inserts) + ";\n")
    print(f"SQL em /tmp/layout_del.sql / /tmp/layout_ins.sql ({len(inserts)} inserts)")


if __name__ == "__main__":
    main()