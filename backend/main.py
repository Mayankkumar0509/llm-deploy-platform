from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# DATABASE (POSTGRESQL)
# ===============================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("❌ DATABASE_URL not found in environment variables.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ===============================
# MODELS
# ===============================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    task_template = Column(String)
    repo_url = Column(String)
    branch = Column(String)
    deployed_url = Column(String)
    logs = Column(Text)


Base.metadata.create_all(bind=engine)

# ===============================
# AUTHENTICATION
# ===============================

SECRET_KEY = "super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10000

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ===============================
# REQUEST MODELS
# ===============================

class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class DeploymentRequest(BaseModel):
    task_template: str
    repo_url: str
    branch: str = "main"
    evaluation_url: str | None = None


# ===============================
# ROUTES
# ===============================

@app.post("/auth/register")
def register_user(data: RegisterRequest):
    db = SessionLocal()

    user_exists = db.query(User).filter(User.email == data.email).first()
    if user_exists:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_password = pwd_context.hash(data.password)
    new_user = User(email=data.email, password=hashed_password)

    db.add(new_user)
    db.commit()
    db.close()

    return {"message": "User registered successfully"}


@app.post("/auth/login")
def login(data: LoginRequest):
    db = SessionLocal()

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if not pwd_context.verify(data.password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect password")

    token = create_access_token({"sub": user.email})
    db.close()
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me")
def get_current_user(email: str = Depends(verify_token)):
    return {"email": email}


@app.post("/deploy")
def deploy_model(req: DeploymentRequest, email: str = Depends(verify_token)):
    db = SessionLocal()

    new_deployment = Deployment(
        user_email=email,
        task_template=req.task_template,
        repo_url=req.repo_url,
        branch=req.branch,
        deployed_url="https://render.com/example-url?",
        logs="Deployment started..."
    )

    db.add(new_deployment)
    db.commit()
    db.close()

    return {"message": "Deployment created", "deployment": new_deployment.id}


@app.get("/deployments")
def get_user_deployments(email: str = Depends(verify_token)):
    db = SessionLocal()
    deployments = db.query(Deployment).filter(Deployment.user_email == email).all()
    db.close()
    return deployments


@app.get("/")
def root():
    return {"message": "Backend is running!"}

