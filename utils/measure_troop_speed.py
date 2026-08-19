#!/usr/bin/env python3
"""Mede a velocidade REAL de uma tropa em campo (tiles/segundo) para calibrar a
conversao movement_speed(raw) -> tiles/s.

Estrategia: acha a tropa UMA vez (scan da heap, ~2s), guarda o endereco do
objeto, e depois rele SO aquele endereco (subtiles fracionarios) num loop
apertado com time.perf_counter(). Reler um endereco conhecido custa
microssegundos, entao a medicao de velocidade fica precisa.

Ideal medir uma tropa VOADORA (voa em linha reta, sem pathing de muralha =
velocidade constante). Roda como: sudo -n python3 utils/measure_troop_speed.py [did]
(default did=4000008 Dragao). Precisa de tropa em campo (deploye antes).
"""
import importlib.util
import math
import struct
import sys
import time

_SPEC = importlib.util.spec_from_file_location(
    "mem_reader", "/home/gebra/.local/share/coc-digital-twin/mem_reader.py")
mr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mr)  # seguro: main() esta sob if __name__


def find_troop_addr(pid, base, want_did):
    """Varre a heap por objetos-tropa com data-id == want_did e subtiles sadios;
    retorna o endereco do objeto com maior eid (o deployado mais recente)."""
    import numpy as np
    _, regions = mr.find_libg_base(pid)
    VT_LO, VT_HI = base + 0x1600000, base + 0x1790000
    best = None  # (eid, addr)
    with open(f"/proc/{pid}/mem", "rb", 0) as fmem:
        def rq(a):
            fmem.seek(a); return struct.unpack_from("<Q", fmem.read(8), 0)[0]
        def ri(a):
            fmem.seek(a); return struct.unpack_from("<i", fmem.read(4), 0)[0]
        for lo, hi, name in mr.anon_rw_regions(pid, regions):
            try:
                fmem.seek(lo); buf = fmem.read(hi - lo)
            except (OSError, OverflowError):
                continue
            n = len(buf) // 8
            if not n:
                continue
            arr = np.frombuffer(buf, dtype=np.uint64, count=n)
            cand = np.nonzero((arr >= VT_LO) & (arr < VT_HI))[0]
            for i in cand:
                a = lo + int(i) * 8
                try:
                    core = rq(a + 0x08)
                    did = ri(rq(core + 0x18) + 0x18)
                    if did != want_did:
                        continue
                    subx, suby = ri(core + 0x20), ri(core + 0x24)
                    if not (0 <= subx <= 48 * 512 and 0 <= suby <= 48 * 512):
                        continue  # descarta lixo/tropa morta
                    eid = ri(a + 0x20)
                except (OSError, OverflowError):
                    continue
                if best is None or eid > best[0]:
                    best = (eid, a)
    return best[1] if best else None


def read_subtiles(pid, addr):
    with open(f"/proc/{pid}/mem", "rb", 0) as fmem:
        def rq(a):
            fmem.seek(a); return struct.unpack_from("<Q", fmem.read(8), 0)[0]
        def ri(a):
            fmem.seek(a); return struct.unpack_from("<i", fmem.read(4), 0)[0]
        core = rq(addr + 0x08)
        return ri(core + 0x20), ri(core + 0x24)


def main():
    want_did = int(sys.argv[1]) if len(sys.argv) > 1 else 4000008
    pid = mr.find_game_pid()
    if not pid:
        print("[!] jogo nao encontrado"); sys.exit(1)
    base, _ = mr.find_libg_base(pid)
    print(f"[+] pid={pid} base={hex(base)} procurando tropa did={want_did}...")

    addr = find_troop_addr(pid, base, want_did)
    if not addr:
        print("[!] tropa nao encontrada — deploye a tropa e rode de novo"); sys.exit(1)
    print(f"[+] tropa @ {hex(addr)} — amostrando posicao por ~4s...")

    samples = []  # (t, sx, sy)
    t_end = time.perf_counter() + 4.0
    while time.perf_counter() < t_end:
        t = time.perf_counter()
        try:
            sx, sy = read_subtiles(pid, addr)
        except OSError:
            break
        samples.append((t, sx, sy))
        time.sleep(0.05)

    # velocidade instantanea entre amostras consecutivas (em tiles/s),
    # ignorando amostras paradas (tropa atacando/bloqueada = v~0)
    speeds = []
    for (t0, x0, y0), (t1, x1, y1) in zip(samples, samples[1:]):
        dt = t1 - t0
        if dt <= 0:
            continue
        dtile = math.hypot((x1 - x0), (y1 - y0)) / 512.0
        v = dtile / dt
        speeds.append(v)

    moving = [v for v in speeds if v > 0.05]  # so trechos em movimento
    if not moving:
        print("[!] tropa nao se moveu (ja estava atacando?) — tente deploy mais longe da base")
        print(f"    ({len(samples)} amostras, todas paradas)")
        sys.exit(1)

    moving.sort()
    med = moving[len(moving) // 2]
    mean = sum(moving) / len(moving)
    t = mr  # noop
    troop = None
    import json
    td = json.load(open("/home/gebra/COC_script/utils/troop_data.json")).get(str(want_did))
    raw = td["movement_speed"] if td else None
    name = td["name"] if td else "?"

    print(f"\n[resultado] tropa={name} did={want_did}")
    print(f"  amostras={len(samples)} em_movimento={len(moving)}")
    print(f"  velocidade medida: mediana={med:.3f} tiles/s  media={mean:.3f} tiles/s")
    if raw:
        print(f"  movement_speed(raw)={raw}")
        print(f"  razao raw/tiles_por_s: mediana->{raw/med:.1f}  media->{raw/mean:.1f}")
        print(f"  (hipoteses comuns: raw/100={raw/100:.2f} tiles/s ; raw/8/... etc.)")


if __name__ == "__main__":
    main()
