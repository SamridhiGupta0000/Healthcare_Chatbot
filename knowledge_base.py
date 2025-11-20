import os
import re
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

MAP_PATH = os.path.join(DATA_DIR, "symptom_disease_mapping.csv")
DESC_PATH = os.path.join(DATA_DIR, "symptom_Description.csv")
PREC_PATH = os.path.join(DATA_DIR, "symptom_precaution.csv")

# ---------------- CSV loader ----------------
def _read_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required file not found: {path}")
    return pd.read_csv(path, engine="python", on_bad_lines="skip")


mapping_df = _read_csv(MAP_PATH)
description_df = _read_csv(DESC_PATH)
precaution_df = _read_csv(PREC_PATH)

# Normalize column names
mapping_df.columns = [c.strip() for c in mapping_df.columns]
description_df.columns = [c.strip() for c in description_df.columns]
precaution_df.columns = [c.strip() for c in precaution_df.columns]

# ---------------- Build records ----------------
disease_records = []
for _, row in mapping_df.iterrows():
    disease = str(row.get("Disease", "")).strip()
    raw_symptoms = str(row.get("Symptoms", "")).strip()

    # Accept both ; and , separators in symptoms field
    symptoms_list = [s.strip().lower() for s in re.split(r'[;,]', raw_symptoms) if s.strip()]

    try:
        min_d = int(row.get("Min_Duration", 0))
    except:
        min_d = 0
    try:
        max_d = int(row.get("Max_Duration", 9999))
    except:
        max_d = 9999

    severity_label = str(row.get("Severity", "")).strip().capitalize() or "Unknown"

    # description lookup
    desc = ""
    if "Description" in description_df.columns:
        dr = description_df[description_df["Disease"].str.lower() == disease.lower()]
        if not dr.empty:
            desc = str(dr.iloc[0]["Description"]).strip()

    # precaution lookup
    precs = []
    pr = precaution_df[precaution_df["Disease"].str.lower() == disease.lower()]
    if not pr.empty:
        for col in precaution_df.columns:
            if col.lower().startswith("precaution"):
                v = pr.iloc[0].get(col)
                if pd.notna(v) and str(v).strip():
                    precs.append(str(v).strip())

    # fallback description for simple 'viral fever' or 'fever'
    if not desc and ("viral" in disease.lower() or disease.lower() in ["viral fever", "fever"]):
        desc = ("A viral fever is usually caused by common viruses and typically "
                "causes short-term fever, body ache and fatigue. Most viral fevers "
                "resolve within a few days with rest and fluids.")

    disease_records.append({
        "disease": disease,
        "symptoms": symptoms_list,
        "min_duration": min_d,
        "max_duration": max_d,
        "severity_label": severity_label,
        "description": desc,
        "precautions": precs
    })


# ---------------- Utilities ----------------
def clean_text(text):
    if not text:
        return ""
    t = str(text).lower()
    # keep letters, digits and spaces (digits help parse '2' in '2 days')
    t = re.sub(r'[^a-z0-9\s]', " ", t)
    return re.sub(r'\s+', ' ', t).strip()


def extract_symptom_tokens(user_text):
    """
    Very light-weight tokenizer/keyword extractor.
    - cleans punctuation
    - splits on whitespace
    - returns unique tokens preserving order
    """
    cleaned = clean_text(user_text)
    tokens = [t for t in cleaned.split() if t]
    # simple stemming-ish: common endings (optional, minimal)
    tokens_norm = []
    for t in tokens:
        if t.endswith("ing"):
            t = t[:-3]
        if t.endswith("s") and len(t) > 3:
            t = t[:-1]
        tokens_norm.append(t)
    # deduplicate preserving order
    seen = set()
    out = []
    for t in tokens_norm:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def parse_duration_days(duration_text):
    if not duration_text:
        return 0
    s = str(duration_text).lower()
    s = re.sub(r'[^\d]', '', s)  # remove non-digits
    try:
        return int(s) if s else 0
    except:
        return 0


# ---------------- Duration bucket helper ----------------
def duration_bucket(days):
    # returns a simple bucket name
    if days <= 3:
        return "short"
    if days <= 14:
        return "medium"
    if days <= 45:
        return "long"
    return "chronic"


# ---------------- Scoring & categorization ----------------
def _severity_penalty(severity_label, days):
    s = str(severity_label).lower()
    if "severe" in s:
        base = 0.35
    elif "moderate" in s:
        base = 0.15
    else:
        base = 0.0
    # for short durations, penalize severe more
    if days <= 3:
        base *= 1.2
    return base


def match_disease(user_symptoms, user_duration):
    """
    Returns a structured dict with categorized results and meta:
    {
      "primary": {...} or None,
      "secondary": [...],
      "other": [...],
      "emergency": bool,
      "emergency_reasons": [...],
      "doctor_advice": [...]
    }
    Each disease entry:
      { disease, matched, score, severity, description, precautions, duration_ok, duration_days }
    """
    tokens = extract_symptom_tokens(user_symptoms)
    days = parse_duration_days(user_duration)
    bucket = duration_bucket(days)

    result_candidates = []

    if not tokens:
        return {
            "primary": None,
            "secondary": [],
            "other": [],
            "emergency": False,
            "emergency_reasons": [],
            "doctor_advice": []
        }

    # Compute scores
    for rec in disease_records:
        ds = rec["symptoms"]
        if not ds:
            continue

        # match by simple token containment (tokens vs symptoms words)
        matched = []
        for s in ds:
            s_tokens = [t for t in clean_text(s).split() if t]
            # if any token equals s or is contained in user tokens -> match
            if any(tok in tokens for tok in s_tokens) or any(tok in s_tokens for tok in tokens):
                matched.append(s)

        if not matched:
            continue

        # scoring factors
        match_count = len(matched)
        total_symptoms = max(1, len(ds))
        base_frac = match_count / total_symptoms  # matched fraction

        # duration compatibility
        duration_ok = (days == 0) or (rec["min_duration"] <= days <= rec["max_duration"])
        duration_bonus = 0.45 if duration_ok else 0.0

        # severity penalty & missing symptom penalty
        severity_pen = _severity_penalty(rec["severity_label"], days)
        missing_pen = 0.0
        if total_symptoms >= 3 and base_frac < 0.5:
            missing_pen = 0.25 * (1 - base_frac)

        # viral/fever extra boost (helps surface Viral Fever for short fevers)
        viral_boost = 0.0
        if "fever" in tokens and ("viral" in rec["disease"].lower() or rec["disease"].lower() in ["viral fever", "fever"]):
            if days <= 7:
                viral_boost = 0.5

        score = base_frac + duration_bonus - severity_pen - missing_pen + viral_boost

        result_candidates.append({
            "disease": rec["disease"],
            "matched": matched,
            "score": round(score, 4),
            "severity": rec["severity_label"],
            "description": rec["description"],
            "precautions": rec["precautions"],
            "duration_ok": duration_ok,
            "duration_days": days,
            "match_count": match_count,
            "total_symptoms": total_symptoms
        })

    # No candidates found
    if not result_candidates:
        return {
            "primary": None,
            "secondary": [],
            "other": [],
            "emergency": False,
            "emergency_reasons": [],
            "doctor_advice": []
        }

    # Sort by score desc then match_count
    result_candidates.sort(key=lambda x: (x["score"], x["match_count"]), reverse=True)

    # Determine primary vs secondary vs other using relative thresholds
    primary = result_candidates[0]
    others = result_candidates[1:]

    secondary = []
    other = []

    for cand in others:
        # if score is at least 70% of top score -> secondary
        if cand["score"] >= 0.7 * primary["score"]:
            secondary.append(cand)
        # or if duration_ok and primary duration not ok -> secondary
        elif cand["duration_ok"] and not primary["duration_ok"]:
            secondary.append(cand)
        else:
            other.append(cand)

    # Emergency detection: simple rule-based red flags
    emergency = False
    emergency_reasons = []

    # common red-flag tokens to look for in user input
    red_flags = ["breath", "shortness", "chest", "severe pain", "loss of consciousness", "bleeding", "bleed", "unconscious", "paralysis", "weakness in limb", "vision loss"]
    user_text = clean_text(user_symptoms)
    for rf in red_flags:
        if rf in user_text:
            emergency = True
            emergency_reasons.append(f"Red flag: '{rf}' mentioned")

    # if duration is very long for acute diseases, flag for doctor
    if days > 30:
        emergency = emergency or False
        emergency_reasons.append("Symptom duration > 30 days — consider specialist evaluation")

    # doctor advice bullets (generic)
    doctor_advice = []
    if emergency:
        doctor_advice.append("Seek immediate medical care or emergency services.")
    else:
        # suggestions based on primary severity/duration
        sev = primary["severity"].lower()
        if sev == "severe" or primary["duration_days"] > 14:
            doctor_advice.append("Consult a doctor for evaluation and tests as needed.")
        else:
            doctor_advice.append("Monitor symptoms at home; follow precautions. See a doctor if symptoms worsen or persist.")


    # Final structure
    return {
        "primary": primary,
        "secondary": secondary,
        "other": other,
        "emergency": emergency,
        "emergency_reasons": emergency_reasons,
        "doctor_advice": doctor_advice
    }
