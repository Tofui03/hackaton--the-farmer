# SDOC Verification Console

React + Vite + TypeScript + Tailwind frontend for the Shipping Document Verification API.

## Local development

```powershell
cd frontend
npm install
npm run dev
```

Vite proxies `/api/*` to `http://localhost:10000/*` by default. Start the backend from the repository root with:

```powershell
python main.py
```

## Verification and production build

```powershell
python ../scripts/verify_contracts.py
npm run test
npm run build
```

The Vite production build writes into `../docs/` (serving root for both FastAPI and GitHub Pages). When `docs/assets/` exists, FastAPI serves the built React 18 SPA at `/cases` and `/cases/:email_id/...`.

The UI never computes match/mismatch decisions. It renders canonical `AuditRecord` data and submits source-level `ReviewUpdate` corrections to the backend.
