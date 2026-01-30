# Notes / Todos:

This is a template for a fullstack app, ready to be deployed on cloudfoundry after services are created and bound.

- Stack:

  - pnpm + Vite + Tanstack + React
  - Python + FastAPI
  - cloudfoundry by DyP PaaS

## Quickstart / Full workflow

This section documents a complete workflow from cloning the repo to verifying the deployed app. Replace placeholders (UPPERCASE) with your values.

**NOTE: IF YOU WANT TO USE THIS TEMPLATE FOR A NEW PROJECT YOU NEED TO REPLACE ALL OCCURENCES OF `van-ai-guided-data-entry` with your app name (in .bat/.sh scripts, manifest, etc. best found with search all files)**

#### Prerequisites

- git, pnpm, Node (for frontend), Python 3.10+, pip, virtualenv
- cf CLI logged in and targeted to the correct API endpoint

#### 1. Clone

- `git clone <REPO_URL>`
- `cd cf-react-python-template`

#### 2. Local run (dev)

- Frontend:
  - `cd client`
  - `pnpm install`
  - `pnpm dev`
- Backend:
  - `cd server`
  - create and activate virtual environment
  - `pip install -r requirements.txt`
  - Copy or create .env from .env.example and set required vars (PORT)
  - cd to root again `fastapi dev server/main.py`

#### 3. Create Cloud Foundry space (if not present)

- `cf login -a API_ENDPOINT -u USERNAME -p PASSWORD`
- `cf create-space SPACE_NAME -o ORG_NAME`
- `cf target -o ORG_NAME -s SPACE_NAME`
- In this template, we use the space name `templates`

#### 4. Pre-push

- Run the provided script to prepare assets/manifest:
  - Windows: `.\pre-push.bat`
  - Linux/macOS: `./pre-push.sh`
- This may build the frontend and copy the requirements.txt to the root dir

#### 5. First cf push

- stop all dev py and node servers before you push
- if not already, target the new space with `cf target -s templates`
- `cf push`
- This run might fail as no connection to services could be established as we do not provide secrets and connection details in the manifest

#### 6. Set environment vars

- Fetch the app route from the DyP PaaS online UI app view
- There are helper scripts in the repo:
  - Windows: `.\set-env.bat ROUTE_FROM_INTERFACE`
  - Linux/macOS: `./set-env.sh ROUTE_FROM_INTERFACE`
- After setting env vars, push or restage:
  - `cf push`

#### 7. Test

- Verify the app:
  - Open the route printed by `cf apps` or the route you set.
  - Test API endpoints by interacting with the webapp.
- Check logs if anything fails:
  - `cf logs APP_NAME --recent`

#### Notes and tips

- Keep secrets out of repo. Use CF user-provided services or encrypted store for credentials.
- If your platform auto-provisions service bindings, follow its UI/CLI to confirm bindings and credentials.
- To re-login: cf login -a https://api.system.int.ap1-paas.cloud.corpintra.net --sso