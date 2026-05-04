import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import pickle
import os

class MLEngine:
    def __init__(self, model_path='model.pkl', features_path='features.pkl'):
        self.model_path = model_path
        self.features_path = features_path
        self.model = None
        self.features = None
        self.grade_map = {
            0.0: ('A', 'Low'),
            1.0: ('B', 'Low'),
            2.0: ('C', 'Medium'),
            3.0: ('D', 'Medium'),
            4.0: ('F', 'High')
        }

    def train(self, csv_path):
        if not os.path.exists(csv_path):
            print(f"Error: {csv_path} not found.")
            return False

        df = pd.read_csv(csv_path)
        
        # Features: Age, Gender, Ethnicity, ParentalEducation, StudyTimeWeekly, 
        # Absences, Tutoring, ParentalSupport, Extracurricular, Sports, Music, Volunteering
        X = df.drop(['StudentID', 'GPA', 'GradeClass'], axis=1)
        y = df['GradeClass']
        
        self.features = list(X.columns)
        
        # Stratify ensures the model sees a balanced mix of all grades during training
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Using more trees and balanced weights to improve recall for rare classes
        self.model = RandomForestClassifier(
            n_estimators=500, 
            max_depth=20,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"Training Complete. Accuracy: {accuracy * 100:.2f}%")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        # Save model and features
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
        with open(self.features_path, 'wb') as f:
            pickle.dump(self.features, f)
        
        return True

    def load(self):
        if os.path.exists(self.model_path) and os.path.exists(self.features_path):
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            with open(self.features_path, 'rb') as f:
                self.features = pickle.load(f)
            return True
        return False

    def predict(self, input_data):
        """
        input_data should be a dictionary with keys matching self.features
        """
        if not self.model:
            if not self.load():
                return None
        
        # Ensure all features are present in input_data, default to 0
        ordered_input = [input_data.get(feat, 0) for feat in self.features]
        prediction = self.model.predict([ordered_input])[0]
        
        grade, risk = self.grade_map.get(prediction, ('Unknown', 'Unknown'))
        return {
            'predicted_grade': grade,
            'risk_level': risk,
            'class_index': int(prediction)
        }

if __name__ == "__main__":
    engine = MLEngine()
    engine.train('Student_performance_data _.csv')
