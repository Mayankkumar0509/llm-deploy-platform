# backend/main.py
import os
import sqlite3
import base64
import requests
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pydantic import BaseModel, Field
from dotenv import load_dotenv

import jwt
from passlib.context import CryptContext

# ---------------------------------------------------------
# Load Environment
# ---------------------------------------------------------
load_dotenv()

STUDENT_SECRET = os.getenv("STUDENT_SECRET", "")
STUDENT_EMAIL = os.getenv("STUDENT_EMAIL", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_PAGES_BASE_URL = os.getenv("GITHUB_PAGES_BASE_URL") or (f"https://{GITHUB_USERNAME}.github.io" if GITHUB_USERNAME else None)
AIML_API_KEY = os.getenv("AIML_API_KEY")
AIML_BASE_URL = os.getenv("AIML_BASE_URL")
AIML_MODEL = os.getenv("AIML_MODEL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key")
DEFAULT_EVALUATION_URL = os.getenv("DEFAULT_EVALUATION_URL")  # optional

# Use Argon2 via passlib (works on Python 3.12)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# ---------------------------------------------------------
# FastAPI App Init
# ---------------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Database Setup
# ---------------------------------------------------------
DB_PATH = "database.db"


def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deployments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            task TEXT,
            round INTEGER,
            nonce TEXT,
            repo_url TEXT,
            commit_sha TEXT,
            pages_url TEXT,
            status TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


create_tables()

# ---------------------------------------------------------
# JWT Utils
# ---------------------------------------------------------
def create_access_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        return None


async def get_current_user(request: Request):
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Missing token")

    token = auth.replace("Bearer ", "")
    email = decode_access_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")

    return email

# ---------------------------------------------------------
# Models
# ---------------------------------------------------------
class UserRegister(BaseModel):
    email: str
    password: str


class Attachment(BaseModel):
    name: str
    url: str


class DeploymentRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: Optional[List[str]] = Field(default_factory=list)
    evaluation_url: Optional[str] = None
    attachments: Optional[List[Attachment]] = Field(default_factory=list)
    target_repo: Optional[str] = None  # optional GitHub repo URL provided by user
    target_github_token: Optional[str] = None  # optional user PAT

# ---------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------
@app.post("/auth/register")
def register(data: UserRegister = Body(...)):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email = ?", (data.email,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(400, "User already exists")

    # Optional: basic password length check
    if len(data.password) == 0:
        conn.close()
        raise HTTPException(400, "Password required")

    hashed = pwd_context.hash(data.password)

    cur.execute("INSERT INTO users (email, password) VALUES (?, ?)", (data.email, hashed))
    conn.commit()
    conn.close()

    token = create_access_token(data.email)
    return {"token": token}


@app.post("/auth/login")
def login(data: UserRegister = Body(...)):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT password FROM users WHERE email = ?", (data.email,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(400, "Invalid credentials")

    if not pwd_context.verify(data.password, row[0]):
        raise HTTPException(400, "Invalid credentials")

    token = create_access_token(data.email)
    return {"token": token}


@app.get("/me")
async def me(current_user: str = Depends(get_current_user)):
    return {"email": current_user}

# ---------------------------------------------------------
# Helper Functions (GitHub, LLM, DB logging)
# ---------------------------------------------------------
def log_deployment(email, task, round_, nonce, status, repo=None, commit=None, pages=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO deployments (email, task, round, nonce, repo_url, commit_sha, pages_url, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (email, task, round_, nonce, repo, commit, pages, status))

    conn.commit()
    conn.close()


def generate_code_from_llm(brief: str, attachments: List[Dict[str, Any]]):
    """
    Call an LLM to generate files. If no LLM configs exist, return a simple index.html.
    Expected return: dict of {filename: content_str}
    """
    # Basic guard: if AIML not configured, produce a trivial index.html
    if not AIML_API_KEY or not AIML_BASE_URL:
        index_html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{brief[:60]}</title>
</head>
<body>
  <h1>Generated App</h1>
  <pre>{brief}</pre>
</body>
</html>
"""
        return {"index.html": index_html, "README.md": f"# {brief[:60]}\n\nGenerated fallback README.\n"}
    try:
        prompt = f"You are to write a minimal working GitHub Pages app.\n\nBRIEF:\n{brief}\n\nATTACHMENTS:\n{attachments}\n"
        headers = {
            "Authorization": f"Bearer {AIML_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": AIML_MODEL or "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        res = requests.post(f"{AIML_BASE_URL}/chat/completions", json=payload, headers=headers, timeout=60)
        res.raise_for_status()
        data = res.json()
        # Attempt to extract content reliably
        content = None
        if "choices" in data and len(data["choices"]) > 0:
            msg = data["choices"][0].get("message") or data["choices"][0].get("text")
            if isinstance(msg, dict):
                content = msg.get("content")
            else:
                content = msg
        if not content:
            content = data.get("text") or str(data)
        # Put generated content into index.html (best-effort)
        return {"index.html": content, "README.md": f"# {brief[:60]}\n\nGenerated by LLM.\n"}
    except Exception:
        # fallback
        index_html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>{brief[:60]}</title></head>
<body><pre>{brief}</pre></body>
</html>"""
        return {"index.html": index_html, "README.md": f"# {brief[:60]}\n\nLLM call failed; fallback README.\n"}


def pick_eval_url(provided):
    if provided:
        return provided
    return DEFAULT_EVALUATION_URL  # may be None


def gh_api_headers(token):
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}


def parse_repo_fullname_from_url(repo_url):
    # e.g. https://github.com/owner/repo -> owner/repo
    try:
        p = urlparse(repo_url)
        parts = p.path.strip("/").split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    except Exception:
        return None


def create_repo_with_token(repo_name, token, owner=None):
    """
    Create a repo for the authenticated user if owner is None,
    or attempt to create in an org if owner is provided.
    Returns the html_url of the created repo.
    """
    headers = gh_api_headers(token)
    if owner:
        api_url = f"https://api.github.com/orgs/{owner}/repos"
        payload = {"name": repo_name, "private": False, "auto_init": True}
    else:
        api_url = "https://api.github.com/user/repos"
        payload = {"name": repo_name, "private": False, "auto_init": True}
    r = requests.post(api_url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json().get("html_url")


def upload_file_to_repo_using_token(owner_repo, filepath, content_str, token, branch="main", message=None):
    """
    Upload or update a file using the contents API for a given owner/repo.
    owner_repo: "owner/repo"
    """
    api_url = f"https://api.github.com/repos/{owner_repo}/contents/{filepath}"
    headers = gh_api_headers(token)
    b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    payload = {"message": message or f"Add {filepath}", "content": b64, "branch": branch}
    r = requests.put(api_url, json=payload, headers=headers, timeout=30)
    if r.status_code in (200, 201):
        return r.json()
    # if already exists, try update with sha
    if r.status_code == 422 or r.status_code == 400:
        getr = requests.get(api_url, headers=headers, timeout=20)
        if getr.status_code == 200:
            sha = getr.json().get("sha")
            payload["sha"] = sha
            r2 = requests.put(api_url, json=payload, headers=headers, timeout=30)
            r2.raise_for_status()
            return r2.json()
    r.raise_for_status()


def enable_pages_for_repo(owner_repo, token):
    api = f"https://api.github.com/repos/{owner_repo}/pages"
    headers = gh_api_headers(token)
    payload = {"source": {"branch": "main", "path": "/"}}
    r = requests.post(api, json=payload, headers=headers, timeout=30)
    # GitHub may return 201/202 for pages; return status code
    return r.status_code


def notify_evaluator(evaluation_url, payload):
    headers = {"Content-Type": "application/json"}
    try:
        r = requests.post(evaluation_url, json=payload, headers=headers, timeout=30)
        return r.status_code
    except Exception:
        return None

# ---------------------------------------------------------
# Main endpoint: receive deployment requests
# ---------------------------------------------------------
@app.post("/api-endpoint")
async def api_endpoint(req: DeploymentRequest = Body(...), background: BackgroundTasks = None, raw: Request = None):
    # Instructor requests may post without auth; student requests may include Authorization header (optional)
    # Here we accept requests from frontend (which may include user's token via /auth)
    auth = raw.headers.get("Authorization") if raw else None

    if auth:
        token = auth.replace("Bearer ", "")
        user = decode_access_token(token)
        if not user:
            raise HTTPException(401, "Invalid token")
    else:
        user = req.email  # instructor request or unauthenticated request

    # Verify secret matches STUDENT_SECRET (if provided). Instructors may intentionally send the correct secret.
    if STUDENT_SECRET and req.secret != STUDENT_SECRET:
        raise HTTPException(401, "Invalid secret")

    # log initial processing row
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO deployments (email, task, round, nonce, repo_url, commit_sha, pages_url, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user, req.task, req.round, req.nonce, None, None, None, "processing"))
        deployment_id = cur.lastrowid
        conn.commit()
        conn.close()
    except Exception as e:
        raise HTTPException(500, f"DB error: {e}")

    # Background processing
    if background is not None:
        background.add_task(handle_deployment, req, user, deployment_id)
    else:
        # if background not provided, run inline (not recommended)
        handle_deployment(req, user, deployment_id)

    return {"status": "processing", "deployment_id": deployment_id}


# ---------------------------------------------------------
# Deployment worker
# ---------------------------------------------------------
def handle_deployment(req: DeploymentRequest, user_email: str, deployment_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        # 1) generate files via LLM or fallback
        generated_files = generate_code_from_llm(req.brief, [a.dict() for a in (req.attachments or [])])
        if "README.md" not in generated_files:
            generated_files["README.md"] = f"# {req.task}\n\n{req.brief}\n"

        # decide evaluation_url (priority: request -> DEFAULT_EVALUATION_URL -> None)
        eval_url = pick_eval_url(req.evaluation_url)

        chosen_repo_html = None
        chosen_pages_url = None
        commit_sha = "latest"

        # If user provided target_repo
        if req.target_repo:
            owner_repo = parse_repo_fullname_from_url(req.target_repo)
            if not owner_repo:
                raise Exception("Invalid target_repo URL provided")

            # choose token: user-supplied token first, otherwise system token
            token_to_use = req.target_github_token or GITHUB_TOKEN
            if not token_to_use:
                raise Exception("No GitHub token available to access target repo")

            # ensure repo exists; if not try to create (may fail if token lacks privileges)
            r = requests.get(f"https://api.github.com/repos/{owner_repo}", headers=gh_api_headers(token_to_use), timeout=20)
            if r.status_code == 404:
                # attempt to create repo for the authenticated user (owner of token)
                repo_name = owner_repo.split("/")[-1]
                created_html = create_repo_with_token(repo_name, token_to_use, owner=None)
                chosen_repo_html = created_html
                # set owner_repo to authenticated user's actual repo path
                # attempt to determine owner from token
                me_r = requests.get("https://api.github.com/user", headers=gh_api_headers(token_to_use), timeout=20)
                if me_r.status_code == 200:
                    owner_login = me_r.json().get("login")
                    owner_repo = f"{owner_login}/{repo_name}"
                else:
                    # fallback to requested owner_repo; uploads may fail
                    pass
            else:
                chosen_repo_html = req.target_repo

            # upload files
            for fname, fcontent in generated_files.items():
                upload_file_to_repo_using_token(owner_repo, fname, fcontent, token_to_use, message=f"Add {fname}")

            # enable pages
            try:
                enable_pages_for_repo(owner_repo, token_to_use)
                chosen_pages_url = f"https://{owner_repo.split('/')[0]}.github.io/{owner_repo.split('/')[1]}/"
            except Exception:
                chosen_pages_url = None

        else:
            # create repo under system account
            repo_name = f"{req.task}".replace(" ", "-")[:80]
            created_html = create_repo_with_token(repo_name, GITHUB_TOKEN, owner=None)
            chosen_repo_html = created_html
            owner_repo = f"{GITHUB_USERNAME}/{repo_name}"

            # upload files
            for fname, fcontent in generated_files.items():
                upload_file_to_repo_using_token(owner_repo, fname, fcontent, GITHUB_TOKEN, message=f"Add {fname}")

            # enable pages
            try:
                enable_pages_for_repo(owner_repo, GITHUB_TOKEN)
                if GITHUB_PAGES_BASE_URL:
                    chosen_pages_url = f"{GITHUB_PAGES_BASE_URL.rstrip('/')}/{repo_name}/"
                else:
                    chosen_pages_url = f"https://{GITHUB_USERNAME}.github.io/{repo_name}/" if GITHUB_USERNAME else None
            except Exception:
                chosen_pages_url = None

        # notify evaluator if available
        eval_status = None
        if eval_url:
            notif = {
                "email": user_email,
                "task": req.task,
                "round": req.round,
                "nonce": req.nonce,
                "repo_url": chosen_repo_html,
                "commit_sha": commit_sha,
                "pages_url": chosen_pages_url
            }
            try:
                r = requests.post(eval_url, json=notif, headers={"Content-Type": "application/json"}, timeout=30)
                eval_status = r.status_code
            except Exception:
                eval_status = None

        # update deployment record as success
        cur.execute("""
            UPDATE deployments SET repo_url=?, commit_sha=?, pages_url=?, status=? WHERE id=?
        """, (chosen_repo_html, commit_sha, chosen_pages_url, "success", deployment_id))
        conn.commit()

    except Exception as e:
        # log traceback and update status
        traceback.print_exc()
        try:
            cur.execute("UPDATE deployments SET status=? WHERE id=?", (f"error: {str(e)}", deployment_id))
            conn.commit()
        except Exception:
            pass
    finally:
        conn.close()

# ---------------------------------------------------------
# Get Deployments for current user
# ---------------------------------------------------------
@app.get("/deployments")
async def get_deployments(current_user: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, task, round, nonce, repo_url, commit_sha, pages_url, status, created_at
        FROM deployments
        WHERE email = ?
        ORDER BY created_at DESC
    """, (current_user,))

    rows = cur.fetchall()
    conn.close()

    deployments = []
    for r in rows:
        deployments.append({
            "id": r[0],
            "task": r[1],
            "round": r[2],
            "nonce": r[3],
            "repo_url": r[4],
            "commit_sha": r[5],
            "pages_url": r[6],
            "status": r[7],
            "created_at": r[8]
        })

    return {"deployments": deployments}

# ---------------------------------------------------------
# Root Test
# ---------------------------------------------------------
@app.get("/")
def root():
    return {"status": "Backend is running"}


