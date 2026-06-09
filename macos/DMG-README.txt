Agent OS — installer disk image (Apple Silicon)
================================================

Install: drag "Agent OS.app" onto the Applications folder, then launch it.
First launch: right-click -> Open (unsigned app, Gatekeeper asks once).

The app is a control panel for the Agent OS workspace
(Agent OS spec-driven framework + Activepieces automation engine):

  Start Activepieces        boots Docker + the automation engine
  Open Dashboard            http://localhost:8080
  Stop Activepieces         shuts the engine down
  Open Workspace in Finder  ~/agent-os-workspace
  Install / Repair          full setup in Terminal (Homebrew, git, node,
                            uv, python, Docker Desktop, workspace, secrets)

On first run the app offers installation automatically — everything needed
is bundled inside the app (offline workspace copy included).
