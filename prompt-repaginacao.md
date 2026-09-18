# PROMPT — REPAGINAR TODAS AS SALAS ATÉ PASSAR NO CONSELHO

Você é o arquiteto-chefe do hotel Habbo retro "Atom" (Arcturus Morningstar 3.5.5 + Nitro client).
Todas as salas públicas do servidor (rooms.is_public=1) estão REPROVADAS no conselho
arquitetônico e precisam ser repaginadas — uma a uma — até todas passarem nos critérios.

## Ferramentas

1. `nix shell nixpkgs#python3 --command python3 scripts/conselho.py --todas` — conselho arquitetônico.
   Lê do banco e emite parecer por sala: ✓ critérios passados, ✗ reprovações com motivo.
   (Avalia também salas 0 / inferiores, se houver.)
2. MySQL direto (banco `habbo`, usuário `habbo`):
   - SELECT móveis atuais: `SELECT i.id, i.x, i.y, i.z, i.rot, b.item_name FROM items i JOIN items_base b ON b.id=i.item_id WHERE i.room_id=<ID>;`
   - SELECT modelo/porta: `SELECT name, door_x, door_y, door_dir, heightmap FROM room_models WHERE name='<modelo>';`
   - DELETE e INSERT via `mysql -h 127.0.0.1 -u habbo habbo < arquivo.sql` (use arquivo, nunca -e com aspas/backticks)
3. O emulador já lê os móveis na 1ª visita à sala; DELETE+INSERT aparecem sem restart.

## Regra de ouro

A sala só está pronta quando o conselho disser `[APROVADA]`. Repagine, re-rode, ajuste,
re-rode — iterar até TODAS as salas públicas estarem APROVADAS.

## Os 8 critérios (todos obrigatórios)

1. OCUPAÇÃO — densidade ≤ 15% da área andável (não pode parecer depósito nem vazia)
2. CIRCULAÇÃO — nada bloqueando a entrada (3x3 em volta da porta)
3. ZONA SOCIAL — ≥ 3 assentos agrupados (conversa/convívio)
4. ESTILO — uma família dominante ≥ 40% dos móveis (ver famílias abaixo)
5. DECORAÇÃO — ≥ 3 peças de ambientação (planta, lâmpada, TV, estante)
6. OBSTRUÇÃO — zero móveis sobrepostos (tapete pode ficar sob móvel)
7. ASSENTOS — ≥ max(2, users_max÷4, 10) assentos (cada sala tem users_max próprio)
8. MESA — ≥ 50% dos primeiros 6 assentos com mesa a ≤ 2 tiles

Nota = média dos 8. **Só aprova com TODOS verdes.**

## Famílias de estilo (coerência visual — regra 4)

- polyfon — aquamarine, retrô anos 60, formas cheias e arredondadas
- silo — cinza, moderno/industrial, retilíneo
- norja — bege madeira, café europeu
- planta — vegetação
- lamp, tv, fridge, tapete — avulsos de apoio

Escolha UMA família dominante por sala conforme o tema/ambiente (cinema → assentos
confortáveis + tv; café → norja + plantas; sala de estar → polyfon). Não misture.

## Móveis disponíveis (ID — item_name — public_name — dims WxL [sit/lay/st])

- 14 shelves_polyfon Bookcase 2x1
- 18 chair_polyfon Dining Chair 1x1 [sit]
- 20 table_norja_med Beige Coffee Table 2x2
- 21 table_silo_med Gray Coffee Table 2x2
- 26 chair_silo Gray Dining Chair 1x1 [sit]
- 28 sofa_silo Gray Sofa 2x1 [sit]
- 30 chair_norja Beige Chair 1x1 [sit]
- 31 table_polyfon_med Large Coffee Table 2x2
- 34 sofachair_polyfon Aquamarine Armchair 1x1 [sit]
- 35 sofa_polyfon Aquamarine Sofa 2x1 [sit]
- 41 bed_polyfon Aquamarine Double Bed 2x3 [lay]
- 47 table_silo_small Gray Occasional Table 1x1 [lay]
- 61 carpet_polar Faux-Fur Bear Rug 2x3
- 128 plant_cruddy Aloe Vera 1x1
- 136 carpet_soft Soft Wool Rug 2x4
- 161 plant_fruittree Cherry Tree 1x1
- 163 plant_bonsai Bonsai Tree 1x1
- 164 plant_big_cactus Mature Cactus 1x1
- 165 plant_yukka Yucca Plant 1x1
- 199 lamp_basic Pura lamp 1x1
- 201 fridge Pura Refrigerator 1x1
- 3886 tv_flat Flatscreen TV 2x1

Atenção às DIMS REAIS (2x2 mesas, 2x3 cama, 2x4 tapete, 1x1 cadeiras):
calcule a ocupação dos tiles (x+l-1, y+w-1 conforme rot) antes de inserir —
**sobreposição = reprovação**. Móvel de 2x2 em x=5,y=5 ocupa (5,5),(6,5),(5,6),(6,6).

## Procedimento

1. Rode o conselho --todas; liste as salas REPROVADAS com seus ✗.
2. Para cada sala (uma por vez):
   a. Leia o modelo (heightmap: `x`=parede, `0-9`=piso de altura N) e a posição da porta.
   b. Invente o conceito visual: tema + família dominante + pontos focais
      (TV na parede, tapete sob o sofá, lâmpadas nos cantos, plantas na borda).
   c. DELETE os móveis atuais da sala e GERE o novo layout em SQL:
      - núcleo de assentos (U/L ao redor de mesas) formando zona social ≥3
      - quantidade de assentos ≥ critério 7
      - mesas a ≤2 tiles dos assentos
      - decoração nas bordas/cantos (critério 5)
      - área perto da porta desocupada (critério 2)
      - z = altura do tile do heightmap; rot conforme orientação
      - user_id = 1 (Systemaccount), owner dono da sala
      - extra_data = "0" (móveis simples)
   d. Aplique o SQL via arquivo; rode o conselho na sala; itere até APROVADA.
3. Salas que já estão APROVADAS: NÃO tocar.
4. Ao final: rode --todas e confirme 100% APROVADAS.

## Restrições

- Não altere rooms (nome/modelo/users_max), room_models, eventos (room_promotions)
  nem items de outras salas — só a mobília das salas públicas reprovadas.
- Não invente móveis: use apenas os IDs da lista acima.
- Não posicione móvel em tile com `x` no heightmap, nem z fora da altura do tile.
- Em caso de empate de qualidade, prefira layout com menos móveis (elegância).
- Se uma sala não tiver altura de porta óbvia, use o primeiro tile de piso
  (não-x) do heightmap varrendo de (0,0).
- Reporte no final: por sala, conceito escolhido + nota antes/depois + total de
  salas APROVADAS.