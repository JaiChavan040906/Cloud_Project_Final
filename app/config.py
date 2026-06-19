import os

from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hospital.db")
JWT_SECRET = os.getenv("JWT_SECRET", "Strong-Secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "hospital-events")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "")
