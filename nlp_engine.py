import json
import pandas as pd
import re
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class HealthcareChatbot:
    def __init__(self):
        # Load data
        self.symptom_df = pd.read_csv("data/symptoms_dataset.csv")
        with open("data/health_faq.json", "r") as f:
            self.health_faq = json.load(f)
        self.vectorizer = CountVectorizer().fit(self.symptom_df['symptom'])

    def clean_text(self, text):
        return re.sub(r'[^a-zA-Z\s]', '', text.lower())

    def detect_symptom(self, user_input):
        user_input_clean = self.clean_text(user_input)
        user_vec = self.vectorizer.transform([user_input_clean])
        similarities = cosine_similarity(user_vec, self.vectorizer.transform(self.symptom_df['symptom']))
        best_match_index = similarities.argmax()
        confidence = similarities[0][best_match_index]

        if confidence > 0.3:
            condition = self.symptom_df.iloc[best_match_index]['condition']
            return f"It seems you may have symptoms related to **{condition}**. Please consult a doctor for confirmation."
        else:
            return None

    def faq_response(self, user_input):
        for question, answer in self.health_faq.items():
            if any(word in user_input.lower() for word in question.lower().split()):
                return answer
        return None

    def get_response(self, user_input):
        faq_ans = self.faq_response(user_input)
        if faq_ans:
            return faq_ans
        symptom_ans = self.detect_symptom(user_input)
        if symptom_ans:
            return symptom_ans
        return "I'm not certain about that. Could you rephrase or specify your symptom?"
