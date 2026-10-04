# Addendum to codebook v2: extended check of L2 pairs

Each item now has two record sets:
- **same**: records retrieved for the drug AND the target disease (up to 40 relevance-ranked, kept only if the title or abstract names the drug as a word; occurrences inside a target name such as "mammalian target of rapamycin" are ignored).
- **parent**: up to 6 records for the drug AND a broader or related disease category (shown as parent_term), for example "depression" for treatment-resistant depression.

Apply codebook v2 to the **same** records exactly as before (L0 / L1 / L2).
Then consider the **parent** records: a record proposing, testing or relating the drug to the parent category, but not to the target disease or one of its subtypes, can raise the label to **L1** at most, never to L0.
Final label = the higher of the two (L0 > L1 > L2). Quote the deciding sentence and PMID, and state whether it came from "same" or "parent".
