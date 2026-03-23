#!/usr/bin/env python3
"""
Script per aggiornare le tariffe ARERA nel file data/tariffe_arera.json.
Gira ogni mese tramite GitHub Actions.
"""

import json
import re
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "tariffe_arera.json"


def get_trimestre(d: date) -> str:
    return f"Q{(d.month - 1) // 3 + 1}-{d.year}"


def prossimo_aggiornamento(d: date) -> str:
    mesi_trim = [1, 4, 7, 10]
    for m in mesi_trim:
        if d.month < m:
            return date(d.year, m, 1).isoformat()
    return date(d.year + 1, 1, 1).isoformat()


def carica_json() -> dict:
    if not OUTPUT_FILE.exists():
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        return {
            "_info": {
                "aggiornato_il": "",
                "trimestre": "",
                "prossimo_aggiornamento": ""
            },
            "oneri_sistema": {
                "asos": 0.0,
                "arim": 0.0
            }
        }
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def salva_json(dati: dict):
    """
    Salva il JSON senza notazione scientifica e senza zeri decimali finali.
    """
    testo = json.dumps(dati, indent=2, ensure_ascii=False)

    def formatta_numero(m):
        s = m.group(0)
        if '.' in s or 'e' in s.lower():
            return f"{float(s):.10f}".rstrip('0').rstrip('.')
        return s

    testo = re.sub(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', formatta_numero, testo)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(testo)
    print(f"✅ Salvato: {OUTPUT_FILE}")


def scrape_arera() -> dict | None:
    """
    Tenta di scrapare i valori dalla pagina ARERA.
    Restituisce None se lo scraping fallisce.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; HomeAssistant-bot/1.0)"}
        r = requests.get(
            "https://www.arera.it/it/dati/elenco_cm.htm",
            headers=headers,
            timeout=15
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        testo = soup.get_text()

        nuovi = {}
        m = re.search(r"ASOS[^\d]*(\d+[.,]\d+)", testo)
        if m:
            nuovi["asos"] = float(m.group(1).replace(",", "."))
        m = re.search(r"ARIM[^\d]*(\d+[.,]\d+)", testo)
        if m:
            nuovi["arim"] = float(m.group(1).replace(",", "."))

        if nuovi:
            print(f"📡 Valori trovati via scraping: {nuovi}")
            return nuovi
        else:
            print("⚠️ Scraping riuscito ma nessun valore estratto")
            return None

    except Exception as e:
        print(f"⚠️ Scraping fallito: {e}")
        return None


def main():
    oggi = date.today()
    dati = carica_json()

    print(f"📅 Data: {oggi.isoformat()} — Trimestre: {get_trimestre(oggi)}")

    # Aggiorna metadati — sovrascrive i campi esistenti, non li duplica
    dati["_info"]["aggiornato_il"] = oggi.isoformat()
    dati["_info"]["trimestre"] = get_trimestre(oggi)
    dati["_info"]["prossimo_aggiornamento"] = prossimo_aggiornamento(oggi)

    # Tenta scraping ARERA
    nuovi_valori = scrape_arera()
    if nuovi_valori:
        if "asos" in nuovi_valori:
            dati["oneri_sistema"]["asos"] = nuovi_valori["asos"]
        if "arim" in nuovi_valori:
            dati["oneri_sistema"]["arim"] = nuovi_valori["arim"]
        print("✅ Valori aggiornati da ARERA")
    else:
        print("ℹ️ Nessun aggiornamento automatico — valori esistenti mantenuti")

    salva_json(dati)


if __name__ == "__main__":
    main()
