import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder
import joblib
import os

# Define paths
DATASET_DIR = "../dataset"
CSV_FILE = os.path.join(DATASET_DIR, "data.csv")
BACKEND_DIR = "."

def clean_weight(val):
    if isinstance(val, str):
        val = val.lower().replace(" g", "").replace(" ct", "").replace("carat", "").strip()
        try:
            return float(val)
        except ValueError:
            return None
    return val

def save_encoders():
    print("Loading data...")
    # Load CSV (logic matching notebook)
    try:
        df = pd.read_csv(CSV_FILE, header=None, skiprows=1)
        if len(df.columns) == 7:
            df.columns = ["Category", "ProductURL", "Purity", "GoldWeight", "DiamondWeight", "ImageLink", "Filename"]
        elif len(df.columns) == 6:
             df = pd.read_csv(CSV_FILE)
        
        print("Data loaded. Shape:", df.shape)
        
        # Clean data to match training set
        if 'GoldWeight' in df.columns:
            df['GoldWeight'] = df['GoldWeight'].apply(clean_weight)
        if 'DiamondWeight' in df.columns:
            df['DiamondWeight'] = df['DiamondWeight'].apply(clean_weight)
            
        df = df.dropna(subset=['GoldWeight', 'DiamondWeight', 'Filename'])
        print("After cleaning. Shape:", df.shape)

        # Fit Encoders
        print("Fitting encoders...")
        cat_encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
        purity_encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
        
        cat_encoder.fit(df[['Category']])
        purity_encoder.fit(df[['Purity']])
        
        # Save Encoders
        print("Saving encoders...")
        joblib.dump(cat_encoder, os.path.join(BACKEND_DIR, "cat_encoder.joblib"))
        joblib.dump(purity_encoder, os.path.join(BACKEND_DIR, "purity_encoder.joblib"))
        
        print("Encoders saved successfully.")
        print("Categories:", cat_encoder.categories_)
        print("Purities:", purity_encoder.categories_)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    save_encoders()
