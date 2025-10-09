import os

from dotenv import load_dotenv

# Load your .env file
load_dotenv()

print("OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))
print("COINAPI_KEY:", os.getenv("COINAPI_KEY"))
print("BROKER_API_KEY:", os.getenv("BROKER_API_KEY"))
