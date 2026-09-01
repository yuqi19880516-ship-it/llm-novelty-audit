"""冻结的 12 个研究目标（与 docs/09 一致；2026-06-05 冻结，注册 DOI 10.17605/OSF.IO/C38BD 后）。

统一模板，仅"疾病"变化，消除目标措辞混杂。
"""

GOALS = [
    {"id": "G01", "en": "Acute myeloid leukemia",          "zh": "急性髓系白血病",   "area": "血液肿瘤"},
    {"id": "G02", "en": "Glioblastoma",                    "zh": "胶质母细胞瘤",     "area": "神经肿瘤"},
    {"id": "G03", "en": "Pancreatic ductal adenocarcinoma","zh": "胰腺导管腺癌",     "area": "消化肿瘤"},
    {"id": "G04", "en": "Amyotrophic lateral sclerosis",   "zh": "肌萎缩侧索硬化",   "area": "神经退行"},
    {"id": "G05", "en": "Alzheimer's disease",             "zh": "阿尔茨海默病",     "area": "神经退行"},
    {"id": "G06", "en": "Pulmonary arterial hypertension", "zh": "肺动脉高压",       "area": "心血管"},
    {"id": "G07", "en": "Idiopathic pulmonary fibrosis",   "zh": "特发性肺纤维化",   "area": "呼吸纤维化"},
    {"id": "G08", "en": "Non-alcoholic steatohepatitis",   "zh": "非酒精性脂肪性肝炎", "area": "肝病代谢"},
    {"id": "G09", "en": "Drug-resistant tuberculosis",     "zh": "耐药结核",         "area": "感染"},
    {"id": "G10", "en": "Systemic lupus erythematosus",    "zh": "系统性红斑狼疮",   "area": "自身免疫"},
    {"id": "G11", "en": "Inflammatory bowel disease",      "zh": "炎症性肠病",       "area": "免疫消化"},
    {"id": "G12", "en": "Treatment-resistant depression",  "zh": "难治性抑郁",       "area": "精神"},
]

GOAL_TEMPLATE = "为{zh}（{en}）寻找可重定位的已上市药物及其作用机制"


def goal_prompt(g: dict) -> str:
    return GOAL_TEMPLATE.format(**g)
