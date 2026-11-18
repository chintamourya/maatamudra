# Deploy a demo link (required for submission)

The root `Dockerfile` builds the React app and serves it from FastAPI, so you deploy ONE container.
Run locally first: `docker compose up --build` then open http://localhost:8000.

## 0. Prepare
1. Database: a Postgres connection string (your Supabase `DATABASE_URL`). Tables are created automatically; nothing to run by hand.
2. Azure OpenAI: endpoint, key and **deployment name** (e.g. gpt-5-mini) of a model that supports structured outputs and tool calling.
3. Case law: an Indian Kanoon API token if you have one; otherwise `TAVILY_API_KEY` works as a fallback.
4. Put them in `.env` (copy `.env.example`) for local runs. Never commit `.env`; the repo ignores it.

## 1. Push to GitHub (required for submission)
```bash
git init && git add . && git commit -m "Vachan"
git branch -M main
git remote add origin https://github.com/<you>/vachan.git
git push -u origin main
```

## 2A. Azure Container Apps (you already use Azure)
Check each flag against `az containerapp --help` if a command errors; the CLI changes.
```bash
az login
az group create -n vachan-rg -l centralindia
az acr create -g vachan-rg -n <uniqueacrname> --sku Basic --admin-enabled true
az acr build -r <uniqueacrname> -t vachan:latest .          # builds in the cloud from the Dockerfile
az containerapp env create -g vachan-rg -n vachan-env -l centralindia
az containerapp create -g vachan-rg -n vachan --environment vachan-env \
  --image <uniqueacrname>.azurecr.io/vachan:latest \
  --registry-server <uniqueacrname>.azurecr.io \
  --registry-username <uniqueacrname> \
  --registry-password "$(az acr credential show -n <uniqueacrname> --query 'passwords[0].value' -o tsv)" \
  --target-port 8000 --ingress external --min-replicas 1 \
  --secrets azkey=<AZURE_OPENAI_API_KEY> dburl=<DATABASE_URL> tvkey=<TAVILY_API_KEY> \
  --env-vars AZURE_OPENAI_ENDPOINT=<endpoint> AZURE_OPENAI_API_KEY=secretref:azkey \
             AZURE_OPENAI_API_VERSION=2024-12-01-preview AZURE_OPENAI_DEPLOYMENT=<deployment> \
             LLM_REASONING_EFFORT=low DATABASE_URL=secretref:dburl TAVILY_API_KEY=secretref:tvkey
# add INDIANKANOON_API_TOKEN as another secret if you have a token
az containerapp show -g vachan-rg -n vachan --query properties.configuration.ingress.fqdn -o tsv
```
That last command prints your demo URL. `--min-replicas 1` avoids a cold start during judging.

## 2B. Any Docker host (Render, Railway, Fly)
Point it at the repo, choose Docker, set the same environment variables, expose the port from `$PORT`.

## 3. Before you submit
- Open the URL, click **Use sample details**, **Draft agreement**, run each tab once.
- Run **Find and check case law** on your demo clauses so results are cached in Supabase.
- Wake the Supabase project if it paused. Warming the cache needs a case-law source.
- Check `GET /api/health`: `"db":"postgres"`, `"llm_configured":true`, and a `case_law_source` that is not `none`.
