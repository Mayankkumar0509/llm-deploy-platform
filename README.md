# 🚀 LLM Code Deployment Platform

A complete end-to-end system for generating, deploying, updating, and publishing apps automatically using LLMs.  
Users can log in, create deployment tasks, generate code with LLMs, push it to GitHub, publish via GitHub Pages, and track deployment history — all from a clean, mobile-friendly UI.

---

## 📌 Features

### 🔹 Frontend (Next.js + Tailwind)
- Full authentication (login/register)
- Dashboard for creating deployment tasks
- Built-in templates + custom task support
- Optional attachments upload
- Optional evaluation URL
- Optional GitHub repo + GitHub token
- Mobile-responsive UI
- Dark mode with toggle
- Recent deployments section
- Beautiful modal result popup

### 🔹 Backend (FastAPI)
- JWT authentication
- Argon2 password hashing
- Accepts deployment tasks via POST
- Generates code using LLM (or fallback)
- Pushes code to GitHub
- Enables GitHub Pages
- Notifies evaluation servers
- Tracks deployments in SQLite
- Background task handling

---

## 📁 Project Structure

