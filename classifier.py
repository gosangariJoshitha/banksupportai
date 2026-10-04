import joblib

# Load trained model
model = joblib.load("models/banking77_classifier.pkl")


def classify_ticket(text):
    prediction = model.predict([text])[0]
    
    probabilities = model.predict_proba([text])[0]
    confidence = max(probabilities) * 100

    return prediction, confidence


# Test
if __name__ == "__main__":
    text = "My ATM did not give me cash but the money was deducted"
    
    category, confidence = classify_ticket(text)

    print("Category:", category)
    print("Confidence:", round(confidence, 2), "%")