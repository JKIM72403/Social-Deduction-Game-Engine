import os
from pymongo import MongoClient

# MongoDB is optional - only initialize if URI is provided
MONGO_URI = os.getenv("MONGODB_URI")
client = None
db = None

if MONGO_URI:
    client = MongoClient(MONGO_URI)
    db = client["social_deduction"]
else:
    # MongoDB not configured - game state features will be disabled
    print("Warning: MONGODB_URI not set. MongoDB features disabled.")
