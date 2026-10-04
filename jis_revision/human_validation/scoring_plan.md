# Scoring plan for the human validation (to be lodged on OSF before the expert workbooks are unblinded)

Sample: 150 of the 300 read drug–disease pairs, stratified by the first machine coder's label (81 L0, 35 L1, 34 L2; seed 20261005).
Coders: two domain experts outside the author team (pharmacology or clinical medicine), blind to machine labels and to each other, using codebook v2 and the same records. Experts are instructed not to use AI tools for reading, translation or searching, and sign a declaration of independence and non-authorship. Each expert's original labels are frozen once returned. Disagreements are resolved by discussion between the two experts (or a third expert) and recorded in an adjudication workbook before comparison with the machine labels.

Primary statistics (script score_human.py):
1. Human–human Cohen's κ on all 150 items.
2. Adjudicated consensus versus the first-pass machine label (the label assigned from the same six records the experts read; the extended re-check, which used more records, is validated separately by item 4): Cohen's κ with bootstrap 95% CI; stratum-weighted agreement; per-level machine precision and recall (weighted to the read-pair distribution).
3. Human-reweighted prior-knowledge share (L0∪L1) for the full 398-item sample, with stratified bootstrap 95% CI; zero-co-occurrence items keep their L2 label.

4. Free-search check of unlinked pairs: the two experts independently search PubMed and Google Scholar, without date restriction other than T, for 30 randomly drawn pairs coded L2 with no co-occurring record (seed 20261006), recording any prior therapeutic proposal (L0) or stated link (L1) for the target disease. Reported: share of the 30 confirmed as L2 under the primary construct, with Wilson 95% CI. Disease scope follows the primary construct: the target disease and its subtypes, with the parent category counted as equivalent for pancreatic ductal adenocarcinoma (pancreatic cancer), idiopathic pulmonary fibrosis (pulmonary fibrosis, including bleomycin models) and non-alcoholic steatohepatitis (NAFLD/MASLD); sources on other broader categories are recorded separately and reported as a sensitivity result (broad construct).

Decision rules (fixed in advance):
- Validity gate (preregistered): consensus–machine κ ≥ 0.70. If it is met, machine labels remain primary and the human-reweighted share is reported alongside.
- If κ < 0.70, the human-reweighted estimates become primary throughout, and the machine labels are reported as secondary.
- Machine L0 precision is required to be at least 0.90 and L2 precision at least 0.80 (stratum-weighted); the free-search check is required to confirm at least 80% of the 30 zero-co-occurrence L2 pairs. Failing either, the corresponding estimates are reported as upper bounds and the human figures as primary.
- H1 is reported as supported only if the lower bound of the primary estimate's 95% CI exceeds 50%.
