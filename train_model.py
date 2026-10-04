import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion
from sklearn.pipeline import Pipeline
import joblib
import os

# Load training dataset
train_data = pd.read_csv("dataset/banking77/train.csv")

X = train_data["text"]
y = train_data["category"]

# Word + Character TF-IDF
features = FeatureUnion([
    (
        "word_tfidf",
        TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1
        )
    ),
    (
        "char_tfidf",
        TfidfVectorizer(
            lowercase=True,
            analyzer="char",
            ngram_range=(3, 5),
            sublinear_tf=True,
            min_df=2
        )
    )
])

# Model
model = Pipeline([
    ("features", features),
    ("classifier", LogisticRegression(
        max_iter=2000,
        C=5
    ))
])

print("Training model...")

model.fit(X, y)

# Save model
os.makedirs("models", exist_ok=True)

joblib.dump(
    model,
    "models/banking77_classifier.pkl"
)

print("Training model completed!")
print("Model saved at: models/banking77_classifier.pkl")