import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables from .env file
load_dotenv()

mongourl = os.getenv("mongodb")

def connectdb():
    client = MongoClient(mongourl)
    db = client["study-mart"]
    return db


