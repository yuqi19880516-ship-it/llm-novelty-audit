# Codebook v2: prior-literature status of a drug–disease pair

Each item is a drug A and a target disease C, with up to six PubMed records (title and complete abstract) published before 5 June 2026 that match A AND C under PubMed's automatic term mapping (MeSH headings, synonyms and subtypes). Records are relevance-ranked; retracted publications are excluded. Judge only from the records shown. You are not told which system or model proposed the pair, its rank, or its self-rated novelty.

Assign exactly one label.

**L0 — prior therapeutic proposal.** At least one record proposes, tests, recommends or reports A (or a salt or formulation of A) as a treatment, prevention or adjunct for C or for a subtype of C. Any study type counts: clinical trial, observational study, case report of therapeutic use, preclinical study in a model of C, or a review that names A as a candidate therapy for C.

**L1 — prior link without a therapeutic proposal.** No record meets L0, but at least one record states a substantive relation between A and C: a mechanistic or pharmacological relation (for example, A acts on a target or pathway the record ties to C), an epidemiological association, an adverse effect of A that causes or worsens C, or drug–disease interaction data.

**L2 — no prior link.** No record states a relation between A and C. Use L2 when the records are absent, when A and C are mentioned only incidentally in the same record (for example, a case report of a patient with C who also takes A for another condition, or a list of unrelated items), or when the match is spurious (homonym or unrelated abbreviation).

Rules:
1. A record about a different disease that merely shares a word with C does not count.
2. A record about a drug class counts only if it names A explicitly.
3. When in doubt between L0 and L1, choose L1; between L1 and L2, choose L1 only if the record asserts a relation, not mere co-mention.
4. Quote the sentence that decides the label and give its PMID; for L2 write "none".

Output per item: `{"key": "<drug||disease>", "label": "L0|L1|L2", "pmid": "...", "quote": "..."}`
