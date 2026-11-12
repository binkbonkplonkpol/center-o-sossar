# Centersveket 🍀

*Svenska först, English below.*

En statisk webbsida som visar hur Socialdemokraterna (S), Vänsterpartiet (V), Miljöpartiet (MP), Centerpartiet (C) och Sverigedemokraterna (SD) röstar i riksdagens voteringar, från riksmötet 2026/27 och framåt.

## Byggt med Claude

Den här sidan och koden i repot är byggda i samarbete med [Claude](https://claude.ai), en AI-assistent från Anthropic. Texterna och ställningstagandena på sidan är projektägarens egna.

## Hur det fungerar

- **Data:** Voteringsdata hämtas automatiskt varje natt från [Riksdagens öppna data](https://www.riksdagen.se/sv/dokument-och-lagar/riksdagens-oppna-data/) (API) av ett GitHub Actions-jobb (`.github/workflows/uppdatera.yml`) som kör `fetch_data.py` och sparar resultatet i `data.json`.
- **Sidan:** `index.html` läser `data.json` och räknar ut en kategori per votering:

| Kategori | Betydelse |
|---|---|
| Alla lika | S, C, V och MP röstar lika |
| Olika position | S, V och MP röstar lika, C annorlunda |
| Röstar med SD | S, V och MP röstar lika, C röstar med SD |
| Blandad röstning | S, V och MP röstar inte lika |

Ett partis position är det alternativ (Ja, Nej eller Avstår) som flest av partiets ledamöter röstade på. Frånvarande räknas inte in.

## Begränsningar

- Endast huvudvoteringar ingår, och beslut som fattats utan votering syns inte.
- Sidan gör ingen bedömning av vilken typ av votering det gäller. Informationen ska ses som en fingervisning.
- Titlar och länkar hämtas från riksdagens dokument för respektive votering.

## Filer

| Fil | Innehåll |
|---|---|
| `index.html` | Hela sidan (HTML, CSS och JavaScript) |
| `fetch_data.py` | Hämtar och sammanställer data från riksdagens API |
| `data.json` | Genererad data, uppdateras av workflowet |
| `.github/workflows/uppdatera.yml` | Nattligt schemalagt jobb |
| `favicon.*`, `apple-touch-icon.png` | Ikoner |

## Köra lokalt

```
python fetch_data.py
python -m http.server
```

Öppna sedan `http://localhost:8000`.

## Källa och ansvar

Källa: Sveriges riksdag. Sidan drivs inte av Sveriges riksdag.

---

## English

A static web page showing how the Swedish parties S, V, MP, C and SD vote in Riksdag roll-call votes, from the 2026/27 session onwards.

**Built with Claude.** This page and the code in this repository were built in collaboration with [Claude](https://claude.ai), an AI assistant from Anthropic. The texts and positions expressed on the page are the project owner's own.

Data is fetched automatically every night from the Riksdag's open data API via a GitHub Actions workflow. Only main votes are included, and the page makes no judgement about the type of vote, so the results should be seen as an indication only. Source: Sveriges riksdag (the Swedish Parliament). This site is not operated by the Riksdag.
