"""
Hämtar voteringsdata för S och C från Sveriges riksdag (data.riksdagen.se)
och skriver data.json. Endast standardbiblioteket används.

Källa: Sveriges riksdag
"""
import json
import time
import xml.etree.ElementTree as ET
import datetime as dt
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://data.riksdagen.se/voteringlista/"
PARTIER = ["S", "C"]
FORSTA_RIKSMOTE = 2026          # 2026/27
SISTA_RIKSMOTE = 2029           # 2029/30 (mandatperiodens sista)
UT = Path(__file__).parent / "data.json"
RADER = ("Ja", "Nej", "Avstår", "Frånvarande")


def riksmoten():
    nu = dt.date.today()
    senaste = nu.year if nu.month >= 9 else nu.year - 1
    senaste = min(max(senaste, FORSTA_RIKSMOTE), SISTA_RIKSMOTE)
    return [f"{y}/{str(y + 1)[2:]}" for y in range(FORSTA_RIKSMOTE, senaste + 1)]


def get_json(url, forsok=3):
    for i in range(forsok):
        try:
            req = Request(url, headers={"User-Agent": "s-c-voteringar/1.0"})
            with urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if i == forsok - 1:
                raise
            time.sleep(3 * (i + 1))


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


def hamta(rm, parti):
    url = BASE + "?" + urlencode(
        {"rm": rm, "parti": parti, "sz": 10000, "utformat": "json"}
    )
    rader, antal = [], None
    while url:
        d = get_json(url)["voteringlista"]
        if antal is None:
            antal = int(d.get("@antal", 0) or 0)
        v = d.get("votering") or []
        rader += [v] if isinstance(v, dict) else v
        url = d.get("@nasta_sida") or None
    if len(rader) < antal:
        raise RuntimeError(
            f"{parti} {rm}: fick {len(rader)} av {antal} rader. "
            "Svaret är trunkerat; delning av anropet krävs."
        )
    return rader


def position(c):
    avgivna = {k: c[k] for k in ("Ja", "Nej", "Avstår")}
    if sum(avgivna.values()) == 0:
        return None
    topp = max(avgivna.values())
    ledare = [k for k, n in avgivna.items() if n == topp]
    return ledare[0] if len(ledare) == 1 else "Delad"


visat_falt = []


def bygg(rm):
    voteringar = {}
    for p in PARTIER:
        for r in hamta(rm, p):
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
                "datum": str(r.get("systemdatum") or r.get("datum") or "")[:10],
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
        if all(p in e for p in PARTIER):
            for p in PARTIER:
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
