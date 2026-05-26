import os
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from classifier import normalize_text

def train_and_evaluate():
    # 1. Load Data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(script_dir, 'scraped_sara_data.xlsx')
    
    if not os.path.exists(excel_path):
        print(f"Error: Dataset not found at {excel_path}")
        print("Please run the scraper first to generate the data.")
        return

    print("Loading dataset...")
    df = pd.read_excel(excel_path)
    
    # Ensure required columns exist
    if 'Tweet Text' not in df.columns or 'Is Cyberbullying (1/0)' not in df.columns:
        print("Error: Dataset is missing required columns ('Tweet Text', 'Is Cyberbullying (1/0)').")
        return

    # Drop any missing values
    df = df.dropna(subset=['Tweet Text', 'Is Cyberbullying (1/0)'])

    # 2. Preprocess Text
    print("Normalizing text data...")
    # Apply the same normalization rules used by the rule-based classifier
    df['Cleaned Text'] = df['Tweet Text'].apply(lambda x: normalize_text(str(x)))
    
    X = df['Cleaned Text']
    y = df['Is Cyberbullying (1/0)'].astype(int)

    # 3. Train-Test Split
    print("Splitting data into 80% training and 20% testing...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print(f"Training samples: {len(X_train)}")
    print(f"Testing samples: {len(X_test)}")

    # 4. Feature Extraction (TF-IDF)
    print("\nExtracting TF-IDF features...")
    vectorizer = TfidfVectorizer(
        max_features=5000, 
        min_df=2, 
        max_df=0.9, 
        ngram_range=(1, 2) # Use unigrams and bigrams
    )
    
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    # 5. Support Vector Machine (SVM)
    print("\n" + "="*50)
    print("Training Support Vector Machine (SVM)...")
    svm_model = SVC(kernel='linear', random_state=42)
    svm_model.fit(X_train_tfidf, y_train)
    
    svm_predictions = svm_model.predict(X_test_tfidf)
    print("\n--- SVM Performance ---")
    print(f"Accuracy: {accuracy_score(y_test, svm_predictions):.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, svm_predictions))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, svm_predictions))

    # 6. Naive Bayes
    print("\n" + "="*50)
    print("Training Naive Bayes (MultinomialNB)...")
    nb_model = MultinomialNB()
    nb_model.fit(X_train_tfidf, y_train)
    
    nb_predictions = nb_model.predict(X_test_tfidf)
    print("\n--- Naive Bayes Performance ---")
    print(f"Accuracy: {accuracy_score(y_test, nb_predictions):.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, nb_predictions))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, nb_predictions))

    # 7. Save Models and Vectorizer
    print("\n" + "="*50)
    print("Saving models to disk...")
    models_dir = os.path.join(script_dir, 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    joblib.dump(vectorizer, os.path.join(models_dir, 'tfidf_vectorizer.joblib'))
    joblib.dump(svm_model, os.path.join(models_dir, 'svm_sara_model.joblib'))
    joblib.dump(nb_model, os.path.join(models_dir, 'nb_sara_model.joblib'))
    
    print(f"Models and vectorizer saved successfully in the '{models_dir}' folder.")
    print("You can load them later using joblib.load() to predict new text!")

if __name__ == "__main__":
    train_and_evaluate()
