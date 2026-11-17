# -*- coding: utf-8 -*-
"""
LogConsult OS — diário de captura: índice dos vídeos/fotos de 09_Fotos.
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Pente-fino nov/2026 (item 4.4 da análise). O vínculo vídeo → cliente → script existia só em
comentários de código. Este script varre os .py desta pasta procurando "IMG_0563",
"IMG_0564-0576", "IMG_0346-0348, IMG_0352" etc., e escreve 09_Fotos/_indice_videos.csv com
uma linha por arquivo:

  arquivo, data, tamanho_mb, status, clientes, scripts, observacao

status:
  transcrito   — citado por um script de mineração (add_<cliente>_precos_contratuais.py ou
                 add_custo_logistico*/add_market_share*), ou seja, o dado está no banco
  citado       — aparece só em outros scripts (conector, correção)
  sem registro — nenhum script cita; ou não foi transcrito, ou a transcrição não deixou rastro

A coluna `observacao` é sua: o que o vídeo mostra, o que ficou ilegível. O script preserva o
que você escrever nela ao rodar de novo.

Uso:  python3 gerar_indice_videos.py
"""
import csv
import datetime
import pathlib
import re

BASE = pathlib.Path(__file__).resolve().parent
FOTOS = BASE.parent / "09_Fotos"
SAIDA = FOTOS / "_indice_videos.csv"

_REF = re.compile(r"IMG_(\d{3,4})((?:\s*(?:[-–]|a|até)\s*(?:IMG_)?\d{3,4})?)", re.I)
_MINERADOR = re.compile(r"^add_(.+?)_(precos_contratuais|fluxos_completos|novos_itens)\.py$|^add_(custo_logistico|market_share)")


def _cliente_do_script(nome):
    m = re.match(r"^(?:add|connect)_(.+?)_(?:precos_contratuais|precos|fluxos_completos|novos_itens|itens)\.py$", nome)
    if m:
        return m[1].upper().replace("_", " ")
    if nome.startswith("add_custo_logistico"):
        return "CUSTO LOGISTICO"
    if nome.startswith("add_market_share"):
        return "MARKET SHARE"
    return None


def referencias():
    """número do vídeo (int) -> [(script, cliente)]"""
    ref = {}
    for py in sorted(BASE.glob("*.py")):
        txt = py.read_text(encoding="utf-8", errors="ignore")
        cli = _cliente_do_script(py.name)
        for m in _REF.finditer(txt):
            a = int(m[1])
            b = a
            if m[2]:
                nb = re.findall(r"\d{3,4}", m[2])
                if nb:
                    b = int(nb[-1])
                    if b < a or b - a > 120:   # faixa implausível = não é faixa
                        b = a
            for n in range(a, b + 1):
                ref.setdefault(n, set()).add((py.name, cli))
    return ref


def main():
    if not FOTOS.exists():
        print(f"pasta não encontrada: {FOTOS}")
        return
    obs_antigas = {}
    if SAIDA.exists():
        with SAIDA.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("observacao"):
                    obs_antigas[r["arquivo"]] = r["observacao"]
    ref = referencias()
    linhas = []
    for f in sorted(FOTOS.iterdir()):
        if f.name.startswith(".") or f.name.startswith("_") or not f.is_file():
            continue
        m = re.search(r"IMG_(\d{3,4})", f.name, re.I)
        n = int(m[1]) if m else None
        quem = sorted(ref.get(n, set())) if n is not None else []
        mineradores = [s for s, _ in quem if _MINERADOR.match(s)]
        status = "transcrito" if mineradores else ("citado" if quem else "sem registro")
        st = f.stat()
        linhas.append({
            "arquivo": f.name,
            "data": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
            "tamanho_mb": round(st.st_size / 1e6, 1),
            "status": status,
            "clientes": "; ".join(sorted({c for _, c in quem if c})),
            "scripts": "; ".join(sorted({s for s, _ in quem})),
            "observacao": obs_antigas.get(f.name, ""),
        })
    with SAIDA.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()) if linhas else ["arquivo"])
        w.writeheader()
        w.writerows(linhas)
    cont = {}
    for l in linhas:
        cont[l["status"]] = cont.get(l["status"], 0) + 1
    mb = {}
    for l in linhas:
        mb[l["status"]] = mb.get(l["status"], 0) + l["tamanho_mb"]
    print(f"{len(linhas)} arquivos indexados em {SAIDA.name}: "
          + ", ".join(f"{k} {v} ({mb[k]/1000:.1f} GB)" for k, v in sorted(cont.items())))


if __name__ == "__main__":
    main()
