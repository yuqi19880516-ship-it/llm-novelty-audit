#!/usr/bin/env python3
"""Post hoc (2026-10-03): for every frame_v2 pair with expanded co-occurrence >= 1, fetch up to K=6 PubMed records
(relevance-ranked, publication date <= T, retracted publications excluded) with title and COMPLETE abstract.
Output: outputs/abstracts_v2.json {"drug||disease": [{"pmid","year","title","abstract","pubtype"}]}"""
import json, os, re, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
T = "2026/06/05"; K = 6; OUT = "outputs/abstracts_v2.json"
ES = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"; EF = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
def get(url):
    for _ in range(6):
        try:
            with urllib.request.urlopen(url, timeout=60) as r: time.sleep(0.36); return r.read().decode()
        except Exception: time.sleep(4)
    return ""
frame = json.load(open("outputs/frame_v2.json")); C = json.load(open("outputs/pubmed_counts_v2.json"))
A = json.load(open(OUT)) if os.path.exists(OUT) else {}
todo = sorted({(r["drug"], r["disease"]) for r in frame if C["pair"]["expanded"].get(f"{r['drug']}||{r['disease']}", 0) >= 1})
print("pairs to fetch", len(todo), flush=True)
for i, (a, c) in enumerate(todo):
    key = f"{a}||{c}"
    if key in A: continue
    term = f"({a}) AND ({c}) NOT retracted publication[pt]"
    p = {"db": "pubmed", "term": term, "retmode": "json", "datetype": "pdat", "mindate": "1800/01/01", "maxdate": T, "retmax": str(K), "sort": "relevance"}
    ids = json.loads(get(ES + "?" + urllib.parse.urlencode(p)) or "{}").get("esearchresult", {}).get("idlist", [])
    recs = []
    if ids:
        x = get(EF + "?" + urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}))
        try:
            root = ET.fromstring(x)
            for art in root.findall(".//PubmedArticle"):
                pmid = art.findtext(".//PMID"); title = "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else ""
                ab = " ".join("".join(t.itertext()) for t in art.findall(".//Abstract/AbstractText"))
                yr = art.findtext(".//PubDate/Year") or (art.findtext(".//PubDate/MedlineDate") or "")[:4]
                pt = "; ".join(t.text or "" for t in art.findall(".//PublicationType"))
                recs.append({"pmid": pmid, "year": yr, "title": title, "abstract": ab, "pubtype": pt})
        except ET.ParseError: pass
    A[key] = recs
    if i % 20 == 0: json.dump(A, open(OUT, "w"), ensure_ascii=False); print(i, key, len(recs), flush=True)
json.dump(A, open(OUT, "w"), ensure_ascii=False); print("done", len(A))
