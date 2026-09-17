#!/usr/bin/env python3
"""
FilterChip nema vlastni pevnou vysku - vyska "pilulky" se odvozuje od
vnitrniho obsahu. Nativni <input type="date"> v Safari vykresluje vyssi
box nez <select>, takze Uzavreni/Fakturace pilulky byly vyssi nez
Vlastnik. Reseni: explicitni vyska na vsech vnitrnich prvcich (select +
oba pary date inputu, height:20 - v ramci FilterChip paddingu 6px+6px
+ 1px border kazda strana to dava celkem 34px na pilulku), a vyhledavaci
pole srovnano na stejnou celkovou vysku (height:34, boxSizing:border-box,
aby to sedelo vedle sebe v jednom radku).

Bezpecne: overuje presny pocet vyskytu PRED zapisem, zaloha puvodniho
souboru vedle nej (.bak).
"""
import sys

JS_PATH = "frontend-admin/app/page.js"

SEARCH_OLD = '''              style={{
                padding: "7px 10px 7px 30px",
                fontSize: 12.5,
                borderRadius: 8,
                border: "1px solid var(--paper-200)",
                width: 260,
              }}'''

SEARCH_NEW = '''              style={{
                padding: "7px 10px 7px 30px",
                fontSize: 12.5,
                borderRadius: 8,
                border: "1px solid var(--paper-200)",
                width: 260,
                height: 34,
                boxSizing: "border-box",
              }}'''

SELECT_OLD = '''            <select
              value={ownerFilter}
              onChange={(e) => setOwnerFilter(e.target.value)}
              style={{ border: "none", fontSize: 12.5, color: "var(--ink-900)", background: "transparent" }}
            >'''

SELECT_NEW = '''            <select
              value={ownerFilter}
              onChange={(e) => setOwnerFilter(e.target.value)}
              style={{ border: "none", fontSize: 12.5, color: "var(--ink-900)", background: "transparent", height: 20 }}
            >'''

CLOSE_DATES_OLD = '''          <FilterChip label="Uzavření">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setPage(1);
              }}
              style={{ border: "none", fontSize: 12.5, color: "var(--ink-600)", background: "transparent" }}
            />
            <span style={{ color: "var(--ink-400)" }}>–</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setPage(1);
              }}
              style={{ border: "none", fontSize: 12.5, color: "var(--ink-600)", background: "transparent" }}
            />
          </FilterChip>'''

CLOSE_DATES_NEW = '''          <FilterChip label="Uzavření">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setPage(1);
              }}
              style={{ border: "none", fontSize: 12.5, color: "var(--ink-600)", background: "transparent", height: 20 }}
            />
            <span style={{ color: "var(--ink-400)" }}>–</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setPage(1);
              }}
              style={{ border: "none", fontSize: 12.5, color: "var(--ink-600)", background: "transparent", height: 20 }}
            />
          </FilterChip>'''

INVOICE_DATES_OLD = '''          <FilterChip label="Fakturace">
            <input
              type="date"
              value={invoiceDateFrom}
              onChange={(e) => {
                setInvoiceDateFrom(e.target.value);
                setPage(1);
              }}
              style={{ border: "none", fontSize: 12.5, color: "var(--ink-600)", background: "transparent" }}
            />
            <span style={{ color: "var(--ink-400)" }}>–</span>
            <input
              type="date"
              value={invoiceDateTo}
              onChange={(e) => {
                setInvoiceDateTo(e.target.value);
                setPage(1);
              }}
              style={{ border: "none", fontSize: 12.5, color: "var(--ink-600)", background: "transparent" }}
            />
          </FilterChip>'''

INVOICE_DATES_NEW = '''          <FilterChip label="Fakturace">
            <input
              type="date"
              value={invoiceDateFrom}
              onChange={(e) => {
                setInvoiceDateFrom(e.target.value);
                setPage(1);
              }}
              style={{ border: "none", fontSize: 12.5, color: "var(--ink-600)", background: "transparent", height: 20 }}
            />
            <span style={{ color: "var(--ink-400)" }}>–</span>
            <input
              type="date"
              value={invoiceDateTo}
              onChange={(e) => {
                setInvoiceDateTo(e.target.value);
                setPage(1);
              }}
              style={{ border: "none", fontSize: 12.5, color: "var(--ink-600)", background: "transparent", height: 20 }}
            />
          </FilterChip>'''


def apply_patch(path, old, new, label):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    count = content.count(old)
    if count == 0:
        print(f"CHYBA: usek '{label}' nebyl v souboru {path} nalezen. Nic jsem nezmenil.")
        sys.exit(1)
    if count > 1:
        print(f"CHYBA: usek '{label}' se v souboru {path} vyskytuje {count}x (ocekavana 1x). Nic jsem nezmenil.")
        sys.exit(1)
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK: usek '{label}' upraven v {path}.")


def backup(path):
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    with open(path + ".bak", "w", encoding="utf-8") as f:
        f.write(data)
    print(f"Zaloha vytvorena: {path}.bak")


if __name__ == "__main__":
    backup(JS_PATH)
    apply_patch(JS_PATH, SEARCH_OLD, SEARCH_NEW, "vyska vyhledavaciho pole")
    apply_patch(JS_PATH, SELECT_OLD, SELECT_NEW, "vyska selectu Vlastnik")
    apply_patch(JS_PATH, CLOSE_DATES_OLD, CLOSE_DATES_NEW, "vyska date inputu Uzavreni")
    apply_patch(JS_PATH, INVOICE_DATES_OLD, INVOICE_DATES_NEW, "vyska date inputu Fakturace")

    print("\nHotovo. Zkontroluj vystup:")
    print(f'  grep -c "height: 20" "{JS_PATH}"')
    print(f'  (mel by ukazat aspon 5 - select + 4 date inputy)')
