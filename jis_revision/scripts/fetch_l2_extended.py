#!/usr/bin/env python3
"""Extended literature check for every pair coded L2, and every pair coded L1 with more than six co-occurring records, with >=1 co-occurring record (system and permutation arms), 2026-10-03.
(a) Retrieve up to 40 relevance-ranked records for (drug) AND (disease) before T and keep those whose title/abstract names
    the drug as a word that is not part of a target name (e.g. 'rapamycin' inside 'target of rapamycin' is ignored);
(b) retrieve up to 6 records for the drug with the PARENT disease category (records on the parent can support at most L1).
Pairs with zero co-occurrence get only (b). Output: outputs/l2_extended.json"""
import json, os, re, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
ES = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"; EF = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
T = "2026/06/05"; OUT = "outputs/l2_extended.json"
PARENT = {"Treatment-resistant depression": "depression", "Drug-resistant tuberculosis": "tuberculosis", "Non-alcoholic steatohepatitis": "non-alcoholic fatty liver disease",
          "Pulmonary arterial hypertension": "pulmonary hypertension", "Idiopathic pulmonary fibrosis": "pulmonary fibrosis", "Pancreatic ductal adenocarcinoma": "pancreatic cancer",
          "Acute myeloid leukemia": "leukemia", "Systemic lupus erythematosus": "lupus", "Inflammatory bowel disease": "colitis", "Glioblastoma": "glioma",
          "Amyotrophic lateral sclerosis": "motor neuron disease", "Alzheimer's disease": "dementia"}
def get(url):
    for _ in range(6):
        try:
            with urllib.request.urlopen(url, timeout=60) as r: time.sleep(0.4); return r.read().decode()
        except Exception: time.sleep(4)
    return ""
def search(term, n):
    p = {"db": "pubmed", "term": term + " NOT retracted publication[pt]", "retmode": "json", "datetype": "pdat", "mindate": "1800/01/01", "maxdate": T, "retmax": str(n), "sort": "relevance"}
    return json.loads(get(ES + "?" + urllib.parse.urlencode(p)) or "{}").get("esearchresult", {}).get("idlist", [])
def fetch(ids):
    out = []
    for i in range(0, len(ids), 20):
        x = get(EF + "?" + urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids[i:i + 20]), "retmode": "xml"}))
        try:
            for art in ET.fromstring(x).findall(".//PubmedArticle"):
                t = art.find(".//ArticleTitle")
                out.append({"pmid": art.findtext(".//PMID"), "year": art.findtext(".//PubDate/Year") or (art.findtext(".//PubDate/MedlineDate") or "")[:4],
                            "title": "".join(t.itertext()) if t is not None else "", "abstract": " ".join("".join(a.itertext()) for a in art.findall(".//Abstract/AbstractText"))})
        except ET.ParseError: pass
    return out
def names_drug(rec, drug):
    txt = (rec["title"] + " " + rec["abstract"]).lower(); d = drug.lower()
    txt = re.sub(r"(mechanistic|mammalian)\s+target\s+of\s+" + re.escape(d), " ", txt)
    return re.search(r"(?<![a-z0-9])" + re.escape(d) + r"(?![a-z0-9])", txt) is not None
fin = json.load(open("coding_materials_v2/final_labels.json")); frame = json.load(open("outputs/frame_v2.json"))
C = json.load(open("outputs/pubmed_counts_v2.json"))["pair"]["expanded"]
BL = json.load(open("outputs/baselines_v3.json"))
PA = {x["key"]: x["label"] for x in json.load(open("coding_materials_v2/coder_A_perm/all.json"))}
PB = {x["key"]: x["label"] for x in json.load(open("coding_materials_v2/coder_B_perm/all.json"))}
PADJ = {x["key"]: x["final_label"] for x in json.load(open("coding_materials_v2/adjudication_perm.json"))}
def plab(k, ex): return "L2" if ex == 0 else (PA[k] if PA[k] == PB[k] else PADJ[k])
pairs = {}
for r in frame:
    k = f"{r['drug']}||{r['disease']}"
    if fin[k] == "L2": pairs[k] = C[k]
for x in BL["perm"]:
    k = f"{x['drug']}||{x['disease']}"
    if x["ex"] >= 0 and plab(k, x["ex"]) == "L2": pairs[k] = x["ex"]
for r in frame:
    k = f"{r['drug']}||{r['disease']}"
    if fin[k] == "L1" and C[k] > 6: pairs[k] = C[k]
for x in BL["perm"]:
    k = f"{x['drug']}||{x['disease']}"
    if x["ex"] > 6 and plab(k, x["ex"]) == "L1": pairs[k] = x["ex"]
A = json.load(open(OUT)) if os.path.exists(OUT) else {}
print("L2 pairs to extend", len(pairs), flush=True)
for i, (k, ex) in enumerate(sorted(pairs.items())):
    if k in A: continue
    drug, dis = k.split("||"); same = []
    if ex >= 1:
        recs = fetch(search(f"({drug}) AND ({dis})", 40)); same = [r for r in recs if names_drug(r, drug)]
    par = [r for r in fetch(search(f"({drug}) AND ({PARENT[dis]})", 6)) if names_drug(r, drug)]
    A[k] = {"same": same, "parent_term": PARENT[dis], "parent": par}
    if i % 10 == 0: json.dump(A, open(OUT, "w"), ensure_ascii=False); print(i, k, len(same), len(par), flush=True)
json.dump(A, open(OUT, "w"), ensure_ascii=False); print("done", len(A))
