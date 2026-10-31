# TinyTravel Ownership & Workflow

## Code Ownership
- **Nikhil (Backend)**: `api/**`, `fixtures/**`, `scripts/**`, `results/**`
- **Rithvik (Frontend)**: `web/**`
- **Shared**: `docs/**`, `README.md`, `.github/**`, root configuration files (touch only after notifying teammate)

## Git Branches
- `backend`: Nikhil's active feature / development branch
- `frontend`: Rithvik's active feature / development branch
- `main`: Stable release branch (protected: PR + green CI required)
- `demo`: Final tagged branch for presentation / event demo

## Merge & Branching Flow
1. Feature work happens exclusively on your own branch (`backend` or `frontend`).
2. At the end of each phase/prompt, open a PR to `main`.
3. Before pushing your branch: always run `git pull --rebase origin main`.
4. Merge PR into `main` once CI is green.
5. **Never force-push (`git push --force`)** to any branch.
6. Never commit `.env`, `node_modules`, `.venv`, `.next`, or `*.db`.
