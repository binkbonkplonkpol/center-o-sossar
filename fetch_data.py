"""
Hämtar voteringsdata för S, C, V, MP och SD från Sveriges riksdag
(data.riksdagen.se) och skriver data.json. Endast standardbiblioteket används.

Källa: Sveriges riksdag
"""
import json
import time
import datetime as dt
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://data.riksdagen.se/voteringlista/"
PARTIER = ["S", "C", "V", "MP", "SD"]
KARNA = ["S", "C"]              # en votering tas med om dessa båda finns
FORSTA_RIKSMOTE = 2026          # 2026/27
SISTA_RIKSMOTE = 2029           # 2029/30 (mandatperiodens sista)
SZ = 10000                      # max antal rader per anrop
UT = Path(__file__).parent / "data.json"
RADER = ("Ja", "Nej", "Avstår", "Frånvarande")


def riksmoten():
    nu = dt.date.today()
    senaste = nu.year if nu.month >= 9 else nu.year - 1
    senaste = min(max(senaste, FORSTA_RIKSMOTE), SISTA_RIKSMOTE)
    return [f"{y}/{str(y + 1)[2:]}" for y in range(FORSTA_RIKSMOTE, senaste + 1)]


def get_bytes(url, forsok=3):
    for i in range(forsok):
        try:
            req = Request(url, headers={"User-Agent": "s-c-voteringar/1.0"})
            with urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:
            if i == forsok - 1:
                raise
            time.sleep(3 * (i + 1))


def get_json(url):
    return json.loads(get_bytes(url))


def hamta_meta(vid):
    """Hämtar titel, datum och länk från röstningens XML-dokument."""
    raw = get_bytes(f"https://data.riksdagen.se/votering/{vid}")
    dok = ET.fromstring(raw).find("dokument")
    if dok is None:
        raise RuntimeError(f"Inget <dokument> i XML för {vid}")

    def t(tag):
        e = dok.find(tag)
        return " ".join((e.text or "").split()) if e is not None else ""

    return {"titel": t("titel"), "datum": t("datum")[:10], "html": t("dokument_url_html")}


def _hamta_url(rm, parti, valkrets=None):
    q = {"rm": rm, "parti": parti, "sz": SZ, "utformat": "json"}
    if valkrets:
        q["valkrets"] = valkrets
    url = BASE + "?" + urlencode(q)
    rader = []
    while url:
        d = get_json(url)["voteringlista"]
        v = d.get("votering") or []
        rader += [v] if isinstance(v, dict) else v
        url = d.get("@nasta_sida") or None
    return rader


def hamta(rm, parti):
    rader = _hamta_url(rm, parti)
    if len(rader) < SZ:
        return rader
    # Svaret nådde taket och kan vara avkortat: dela upp per valkrets.
    print(f"{parti} {rm}: {len(rader)} rader nådde taket, delar upp per valkrets.")
    prov = _hamta_url(rm, parti)
    valkretsar = sorted({r.get("valkrets", "") for r in prov if r.get("valkrets")})
    ut = []
    for vk in valkretsar:
        d = _hamta_url(rm, parti, valkrets=vk)
        if len(d) >= SZ:
            raise RuntimeError(f"{parti} {rm} {vk}: även delat svar nådde taket ({SZ}).")
        ut += d
    return ut


def position(c):
    avgivna = {k: c[k] for k in ("Ja", "Nej", "Avstår")}
    if sum(avgivna.values()) == 0:
        return None
    topp = max(avgivna.values())
    ledare = [k for k, n in avgivna.items() if n == topp]
    return ledare[0] if len(ledare) == 1 else "Delad"


visat_falt = []


def bygg(rm):
    per_parti = {p: hamta(rm, p) for p in PARTIER}

    # Kontroll: alla partier ska ha rader för lika många voteringar.
    antal = {p: len({r.get("votering_id") for r in rader}) for p, rader in per_parti.items()}
    if len(set(antal.values())) > 1:
        print(f"VARNING {rm}: olika antal voteringar per parti: {antal}")

    voteringar = {}
    for p, rader in per_parti.items():
        for r in rader:
            if not visat_falt:
                print("Fält i svaret:", sorted(r))
                visat_falt.append(1)
            try:
                vid = r["votering_id"]
                rost = r["rost"]
            except KeyError:
                raise RuntimeError(f"Oväntade fält i svaret: {sorted(r)}")
            e = voteringar.setdefault(vid, {
                "id": vid,
                "rm": rm,
                "datum": str(r.get("systemdatum") or "")[:10],
                "bet": r.get("beteckning", ""),
                "punkt": str(r.get("punkt", "")),
                "avser": r.get("avser", ""),
                "dok_id": r.get("dok_id", ""),
                "xml": (r.get("votering_url_xml") or "").replace("http://", "https://"),
            })
            c = e.setdefault(p, {k: 0 for k in RADER})
            c[rost] = c.get(rost, 0) + 1

    ut = []
    for e in voteringar.values():
        if all(p in e for p in KARNA):
            for p in PARTIER:
                if p in e:
                    e[p]["position"] = position(e[p])
            ut.append(e)
    ut.sort(key=lambda e: (e["datum"], e["bet"], e["punkt"]))
    return ut


def main():
    gammal = {}
    if UT.exists():
        gammal = json.loads(UT.read_text(encoding="utf-8"))
    cache = {v["id"]: v for v in gammal.get("voteringar", [])}

    alla = []
    for rm in riksmoten():
        alla += bygg(rm)

    # Berika med titel/datum/länk. Redan hämtade titlar återanvänds.
    nya = fel = 0
    for v in alla:
        c = cache.get(v["id"])
        if c and c.get("titel"):
            v.update({k: c[k] for k in ("titel", "datum", "html") if c.get(k)})
            continue
        try:
            meta = hamta_meta(v["id"])
            v.update({k: val for k, val in meta.items() if val})
            nya += 1
            time.sleep(0.2)
        except Exception as e:
            fel += 1
            print(f"Kunde inte hämta titel för {v['id']}: {e}")
    print(f"Titlar: {nya} nya, {fel} misslyckade.")

    # Skriv bara om innehållet ändrats, så att inga onödiga commits skapas.
    if gammal.get("voteringar") == alla:
        print("Ingen förändring.")
        return

    UT.write_text(json.dumps({
        "kalla": "Sveriges riksdag",
        "uppdaterad": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "partier": PARTIER,
        "riksmoten": riksmoten(),
        "voteringar": alla,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Skrev {len(alla)} voteringar.")


if __name__ == "__main__":
    main()
