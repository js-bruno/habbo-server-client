#!/usr/bin/env python3
"""Teste do fluxo de convite: login -> gerar link -> redeimir -> checar espelho."""
import os
import re
import subprocess

import requests

HOST = os.environ.get("HOST", "localhost")
BASE = f"http://{HOST}"
HEADERS = {"Host": "caravelho.com.br", "User-Agent": "habbo-invite-test/1.0"}
MYSQL_PWD = os.environ.get("MYSQL_PWD", "9911")
ADMIN = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "")


def db(sql, db="orioncms"):
    env = dict(os.environ)
    env["MYSQL_PWD"] = MYSQL_PWD
    p = subprocess.run(["mysql", "-h", "127.0.0.1", "-u", "habbo", db, "-N", "-e", sql],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise RuntimeError(f"db: {p.stderr.strip()[:200]}")
    return p.stdout.strip()


def csrf(session, path):
    r = session.get(f"{BASE}{path}", timeout=20)
    m = re.search(r'name="_token" value="([^"]+)"', r.text)
    if not m:
        raise RuntimeError(f"csrf token not found in {path}")
    return m.group(1)


def main():
    s = requests.Session()
    s.headers.update(HEADERS)

    # 1. login admin
    tok = csrf(s, "/")
    r = s.post(f"{BASE}/login", data={"_token": tok, "username": ADMIN, "password": ADMIN_PASS},
               allow_redirects=False, timeout=20)
    if r.status_code != 302 or "/user/me" not in r.headers.get("Location", ""):
        raise RuntimeError(f"login falhou: {r.status_code} -> {r.headers.get('Location')}")
    print("[ok] login admin")

    # 2. gerar convite
    tok = csrf(s, "/user/invite")
    r = s.post(f"{BASE}/user/invite", data={"_token": tok, "max_uses": "1"}, allow_redirects=False, timeout=20)
    if r.status_code != 302:
        raise RuntimeError(f"gerar convite falhou: {r.status_code}")
    code = db("SELECT code FROM invites ORDER BY id DESC LIMIT 1;")
    if not code:
        raise RuntimeError("nenhum invite criado no banco")
    print(f"[ok] convite gerado: {code}")

    # 3. abrir pagina publica do convite (sessao nova = convidado nao logado)
    guest = requests.Session()
    guest.headers.update(HEADERS)
    r = guest.get(f"{BASE}/invite/{code}", timeout=20)
    if r.status_code != 200 or "You have been invited" not in r.text:
        raise RuntimeError(f"pagina do convite falhou: {r.status_code}")
    print("[ok] pagina do convite renderiza")

    # 4. redeimir com username novo
    username = f"convidado{code[:4]}"
    tok = csrf(guest, f"/invite/{code}")
    r = guest.post(f"{BASE}/invite/{code}", data={"_token": tok, "username": username, "terms": "1"},
                   allow_redirects=False, timeout=20)
    if r.status_code != 302:
        raise RuntimeError(f"redeem falhou: {r.status_code}")
    loc = r.headers.get("Location", "")
    if "/invite/success" not in loc:
        raise RuntimeError(f"redirect inesperado: {loc}")
    print(f"[ok] usuario criado, redirect -> {loc}")

    # 5. pagina de sucesso (senha)
    from urllib.parse import urlparse
    success_path = urlparse(loc).path
    r = guest.get(f"{BASE}{success_path}", timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"success falhou: {r.status_code}")
    pw = re.search(r"Password</span>\s*<span[^>]*>([^<]+)</span>", r.text)
    if not pw:
        raise RuntimeError("senha nao encontrada na pagina de sucesso")
    print(f"[ok] senha exibida: {pw.group(1)[:3]}***")

    # 6. checar espelho no banco do jogo
    row = db(f"SELECT id, username, password, rank FROM users WHERE username='{username}';", "habbo")
    if not row:
        raise RuntimeError("usuario NAO espelhado no habbo.users")
    print(f"[ok] espelho habbo.users: {row}")

    # 7. checar settings + currency
    gid = row.split("\t")[0]
    st = db(f"SELECT user_id FROM users_settings WHERE user_id={gid};", "habbo")
    print(f"[ok] users_settings: {st}")
    cur = db(f"SELECT type, amount FROM users_currency WHERE user_id={gid} ORDER BY type;", "habbo")
    print(f"[ok] users_currency: {cur.replace(chr(10), ' | ')}")

    # 8. limpar
    if os.environ.get("SKIP_CLEANUP") != "1":
        db(f"DELETE FROM users_currency WHERE user_id={gid};", "habbo")
        db(f"DELETE FROM users_settings WHERE user_id={gid};", "habbo")
        db(f"DELETE FROM users WHERE id={gid};", "habbo")
        db(f"DELETE FROM invites WHERE code='{code}';")
        db(f"DELETE FROM users WHERE username='{username}';")
        print("[ok] cleanup")

    print("\nFLUXO COMPLETO OK")


if __name__ == "__main__":
    main()