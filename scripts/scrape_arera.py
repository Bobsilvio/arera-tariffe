#!/usr/bin/env python3
"""
Script per scaricare le tariffe ARERA aggiornate.
Aggiorna il file data/tariffe_arera.json con i valori del trimestre corrente.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "tariffe_arera.json"

# URL pagina ARERA componenti tariffarie bassa tensione
ARERA_URL = "https://www.arera.it/it/dati/elenco_cm.htm"

def get_trimestre(d: date) -> str:
    return f"Q{(d.month - 1) // 3 + 1}-{d.year}"

def prossimo_aggiornamento(d: date) -> str:
    mesi_trim = [1, 4, 7, 10]
    for m in mesi_trim:
        if d.month < m:
            return date(d.year, m, 1).isoformat()
    return date(d.year + 1, 1, 1).isoformat()

def carica_json_attuale() -> dict:
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salva_json(dati: dict):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(dati, f, indent=2, ensure_ascii=False)
    print(f"✅ Salvato: {OUTPUT_FILE}")

def scrape_arera() -> dict | None:
    """
    Tenta di scrapare i valori dalla pagina ARERA.
    Se lo scraping fallisce, restituisce None e mantiene i valori esistenti.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; HomeAssistant-bot/1.0)"}
        r = requests.get(ARERA_URL, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        # ARERA cambia spesso la struttura della pagina —
        # qui cerchiamo i valori noti per pattern numerici nelle tabelle
        testo = soup.get_text()

        nuovi = {}

        # Cerca ASOS (componente più stabile da trovare)
        m = re.search(r"ASOS[^\d]*(\d+[.,]\d+)", testo)
        if m:
            nuovi["asos"] = float(m.group(1).replace(",", "."))

        # Cerca ARIM
        m = re.search(r"ARIM[^\d]*(\d+[.,]\d+)", testo)
        if m:
            nuovi["arim"] = float(m.group(1).replace(",", "."))

        if nuovi:
            print(f"📡 Valori trovati via scraping: {nuovi}")
            return nuovi
        else:
            print("⚠️ Scraping riuscito ma nessun valore estratto — pagina ARERA cambiata?")
            return None

    except Exception as e:
        print(f"⚠️ Scraping fallito: {e}")
        return None

def main():
    oggi = date.today()
    dati = carica_json_attuale()

    print(f"📅 Data: {oggi.isoformat()} — Trimestre: {get_trimestre(oggi)}")

    # Aggiorna i metadati
    dati["_info"]["aggiornato_il"] = oggi.isoformat()
    dati["_info"]["trimestre"] = get_trimestre(oggi)
    dati["_info"]["prossimo_aggiornamento"] = prossimo_aggiornamento(oggi)

    # Tenta scraping
    nuovi_valori = scrape_arera()

    if nuovi_valori:
        # Aggiorna solo i valori trovati, mantieni gli altri
        if "asos" in nuovi_valori:
            dati["oneri_sistema"]["asos"] = nuovi_valori["asos"]
        if "arim" in nuovi_valori:
            dati["oneri_sistema"]["arim"] = nuovi_valori["arim"]
        print("✅ Valori aggiornati da ARERA")
    else:
        print("ℹ️ Nessun aggiornamento automatico — valori esistenti mantenuti")
        print("   → Aggiorna manualmente data/tariffe_arera.json se necessario")

    salva_json(dati)

if __name__ == "__main__":
    main()
