import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from pydantic import BaseModel
import tensorflow as tf
import numpy as np
import pandas as pd
import joblib
from PIL import Image
import io
import os

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Gold & Diamond Estimation API")

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Vercel deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model and encoders
# Global variables for model and encoders
model = None
ring_model = None
bangles_model = None
necklace_model = None
earrings_model = None

cat_encoder = None
purity_encoder = None

MODEL_PATH = "gold_diamond_estimation_model.h5"
RING_MODEL_PATH = "gold_diamond_estimator.h5"
BANGLES_MODEL_PATH = "bangles_estimator.keras"
NECKLACE_MODEL_PATH = "necklace_estimator.keras"
EARRINGS_MODEL_PATH = "earrings_estimator.keras"

CAT_ENCODER_PATH = "cat_encoder.joblib"
PURITY_ENCODER_PATH = "purity_encoder.joblib"

# Define a custom Dense layer that ignores 'quantization_config'
@tf.keras.utils.register_keras_serializable()
class PatchedDense(tf.keras.layers.Dense):
    def __init__(self, *args, **kwargs):
        # Filter out the argument causing issues in Keras 3
        if 'quantization_config' in kwargs:
            kwargs.pop('quantization_config')
        super().__init__(*args, **kwargs)

@app.on_event("startup")
async def load_artifacts():
    global model, ring_model, bangles_model, necklace_model, earrings_model, cat_encoder, purity_encoder
    try:
        print(f"Startup: TensorFlow Version: {tf.__version__}")
        try:
             import keras
             print(f"Startup: Keras Version: {keras.__version__}")
        except Exception as k_err:
             print(f"Startup: Could not import keras directly: {k_err}")

        print("Loading models with PatchedDense...")
        
        custom_objects = {'Dense': PatchedDense}

        # Load general model
        if os.path.exists(MODEL_PATH):
             model = tf.keras.models.load_model(MODEL_PATH, custom_objects=custom_objects, compile=False)
             print("General Model loaded successfully.")
        else:
            print(f"Error: General Model file not found at {MODEL_PATH}")

        # Load category models
        models_to_load = {
            "Ring": (RING_MODEL_PATH, "ring_model"),
            "Bangles": (BANGLES_MODEL_PATH, "bangles_model"),
            "Necklace": (NECKLACE_MODEL_PATH, "necklace_model"),
            "Earrings": (EARRINGS_MODEL_PATH, "earrings_model")
        }

        for model_name, (path, global_var_name) in models_to_load.items():
            if os.path.exists(path):
                 loaded_model = tf.keras.models.load_model(path, custom_objects=custom_objects, compile=False)
                 globals()[global_var_name] = loaded_model
                 print(f"{model_name} Model loaded successfully.")
            else:
                 print(f"Error: {model_name} Model file not found at {path}")

        print("Loading encoders...")
        if os.path.exists(CAT_ENCODER_PATH):
            cat_encoder = joblib.load(CAT_ENCODER_PATH)
        else:
             print(f"Error: Category encoder not found at {CAT_ENCODER_PATH}")
             
        if os.path.exists(PURITY_ENCODER_PATH):
            purity_encoder = joblib.load(PURITY_ENCODER_PATH)
        else:
            print(f"Error: Purity encoder not found at {PURITY_ENCODER_PATH}")

        print("Artifacts loading complete.")
    except Exception as e:
        print(f"Error loading artifacts: {e}")

def preprocess_image(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert('RGB')
        img = img.resize((224, 224))
        img_array = np.array(img)
        img_array = img_array / 255.0  # Normalize to [0,1]
        img_array = np.expand_dims(img_array, axis=0) # Add batch dimension
        return img_array
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

def preprocess_tabular(category: str, purity: str, gemstone_present: bool):
    if cat_encoder is None or purity_encoder is None:
        raise HTTPException(status_code=500, detail="Encoders not loaded")
        
    try:
        # Preprocess inputs
        # 1. Category
        cat_df = pd.DataFrame({'Category': [category]})
        cat_features = cat_encoder.transform(cat_df)
        
        # 2. Purity
        purity_df = pd.DataFrame({'Purity': [purity]})
        purity_features = purity_encoder.transform(purity_df)
        
        # 3. Gemstone Presence
        # Training used constant 1.0. We will do the same.
        gemstone_features = np.array([[1.0]])
        
        # Concatenate Tabular Features
        # X_tabular = np.hstack([cat_features, purity_features, gemstone_features])
        X_tabular = np.hstack([cat_features, purity_features, gemstone_features])
        return X_tabular, purity_features
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing tabular data: {e}")

@app.post("/predict")
async def predict(
    image: UploadFile = File(...),
    category: str = Form(...),
    purity: str = Form(...)
):
    if model is None and ring_model is None and bangles_model is None and necklace_model is None and earrings_model is None:
        raise HTTPException(status_code=503, detail="Models not loaded")

    # Read image
    image_bytes = await image.read()
    img_array = preprocess_image(image_bytes)
    
    # Process tabular data
    # We are assuming gemstone presence is 1 based on notebook
    tab_array, purity_array = preprocess_tabular(category, purity, gemstone_present=True)
    
    # Predict
    try:
        predictions = None
        
        if category.lower() == 'ring' and ring_model is not None:
             # Category Models expect [X_img, X_purity]
             predictions = ring_model.predict([img_array, purity_array])
        elif category.lower() == 'bangle' and bangles_model is not None:
             predictions = bangles_model.predict([img_array, purity_array])
        elif category.lower() == 'necklace' and necklace_model is not None:
             predictions = necklace_model.predict([img_array, purity_array])
        elif category.lower() == 'earring' and earrings_model is not None:
             predictions = earrings_model.predict([img_array, purity_array])
        elif model is not None:
             # General Model expects [X_img, X_tabular]
             predictions = model.predict([img_array, tab_array])
        else:
             raise HTTPException(status_code=503, detail=f"Required model for category '{category}' not loaded")
        
        # predictions is a list of arrays: [gold_weight_pred, diamond_weight_pred]
        # safer scalar extraction dealing with potential shape variations
        if isinstance(predictions, list):
            gold_weight = float(np.ravel(predictions[0])[0])
            diamond_weight = float(np.ravel(predictions[1])[0])
        else:
            # Fallback for single array output
            preds_flat = np.ravel(predictions)
            if len(preds_flat) >= 2:
                gold_weight = float(preds_flat[0])
                diamond_weight = float(preds_flat[1])
            else:
                gold_weight = float(preds_flat[0])
                diamond_weight = 0.0

        return {
            "success": True,
            "data": {
                "estimated_value": 0, # Placeholder, calculation needs frontend logic or backend implementation
                "gold_weight": round(gold_weight, 2),
                "diamond_weight": round(diamond_weight, 2),
                "category": category,
                "purity": purity,
                "breakdown": {
                    "gold_value": 0,
                    "stone_value": 0
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
