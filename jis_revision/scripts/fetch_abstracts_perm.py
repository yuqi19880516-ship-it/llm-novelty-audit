#!/usr/bin/env python3
"""Fetch up to 6 relevance-ranked non-retracted records (complete abstracts) for (a) permutation-baseline pairs with >=1
expanded co-occurrence before 2026-06-05 and (b) ripasudil x age-related macular degeneration before 2025-05-28.
Output: outputs/abstracts_perm.json"""
import json, os, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
ES = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"; EF = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"; OUT = "outputs/abstracts_perm.json"
def get(url):
    for _ in range(6):
        try:
            with urllib.request.urlopen(url, timeout=60) as r: time.sleep(0.4); return r.read().decode()
        except Exception: time.sleep(4)
    return ""
def fetch(a, c, T):
    p = {"db": "pubmed", "term": f"({a}) AND ({c}) NOT retracted publication[pt]", "retmode": "json", "datetype": "pdat", "mindate": "1800/01/01", "maxdate": T, "retmax": "6", "sort": "relevance"}
    ids = json.loads(get(ES + "?" + urllib.parse.urlencode(p)) or "{}").get("esearchresult", {}).get("idlist", [])
    recs = []
    if ids:
        try:
            root = ET.fromstring(get(EF + "?" + urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "xml"})))
            for art in root.findall(".//PubmedArticle"):
                t = art.find(".//ArticleTitle")
                recs.append({"pmid": art.findtext(".//PMID"), "year": art.findtext(".//PubDate/Year") or (art.findtext(".//PubDate/MedlineDate") or "")[:4],
                             "title": "".join(t.itertext()) if t is not None else "", "abstract": " ".join("".join(x.itertext()) for x in art.findall(".//Abstract/AbstractText"))})
        except ET.ParseError: pass
    return recs
BL = json.load(open("outputs/baselines_v3.json")); A = json.load(open(OUT)) if os.path.exists(OUT) else {}
todo = sorted({(x["drug"], x["disease"]) for x in BL["perm"] if x["ex"] >= 1})
print("perm pairs", len(todo), flush=True)
for i, (a, c) in enumerate(todo):
    k = f"{a}||{c}"
    if k not in A: A[k] = fetch(a, c, "2026/06/05")
    if i % 25 == 0: json.dump(A, open(OUT, "w"), ensure_ascii=False); print(i, flush=True)
A["Ripasudil||Age-related macular degeneration"] = fetch("Ripasudil", "age-related macular degeneration", "2025/05/28")
json.dump(A, open(OUT, "w"), ensure_ascii=False); print("done", len(A))
