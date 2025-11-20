

#nlp.py

def extract_symptoms(user_input):
    """
    Extracts possible symptoms from user input based on simple keyword matching.
    You can later replace this with NLP or ML model logic.
    """
    symptoms_list = [
        "fever", "cough", "cold", "headache", "fatigue",
        "sore throat", "nausea", "vomiting", "pain", "diarrhea"
    ]
    user_input = user_input.lower()
    extracted = [word for word in symptoms_list if word in user_input]
    return extracted
