# Task Manager with ML-Powered Completion Forecast

A **command-line task manager** backed by **PostgreSQL** and **scikit-learn**.  
Add, update, delete or query tasks—and get an **on-the-spot probability** that a task will finish on time, trained on your own historical data.

---

## ✨ Features
- Full CRUD operations for tasks (title, description, priority 1-5, due date)
- Auto-initialization of PostgreSQL schema
- Machine-learning pipeline:
  - Trains a Linear Regression model when ≥ 10 completed/overdue tasks exist
  - Predicts completion probability for any open task
  - StandardScaler + train/test split + accuracy report
- Env-file configuration for all DB secrets
- Docker & GitHub Actions ready (CI → staging → prod)
