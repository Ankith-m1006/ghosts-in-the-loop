# Running Ghosts in the Loop

Everything runs on one Linux GPU machine (AWS g6.xlarge: 1x L4 24 GB, 4 vCPU, 16 GB; `--profile personal`, ap-south-1).
Stop the instance after every batch. Never leave it running idle.

## Design (6 Nov)
- Real PyPI and npm only. There is no fake registry. An invented name fails with "not found", exactly as it would for a developer.
- **Ghost install attempt** = the agent ran an install for a name the registry reports as not found. That is the exposure: if anyone registered the name, the agent would have installed their code.
- The guard runs in **shadow mode** on every install (`gil/guard.py`, tiers T0 exists, T1 metadata, T2 typosquat, T3 code reading). It records what each tier would block and blocks nothing.
- Set B misspelled names that already exist (`prompts/names_check.json`, 5 of 50 on 6 Nov) are excluded so no run installs a possible live squat.
- Sandboxes: one container per episode (`docker/Dockerfile`), no credentials, caps dropped, 2 GB / 1 CPU, removed after the episode.

## Steps
1. `python -m prompts.hash`: record the SHA-256 of set_a.jsonl and set_b.jsonl in the paper.
2. `python -m scripts.verify_names` (needs internet): refreshes names_check.json.
3. `docker build -t gil-sandbox:latest docker/`
4. Serve a model with an OpenAI-compatible API, one at a time, e.g.
   `vllm serve google/gemma-4-E4B-it --max-model-len 16384` (port 8000), or llama.cpp `llama-server` for GGUF builds.
5. Smoke test: `python -m scripts.run_agent --model openai/google/gemma-4-E4B-it --api-base http://localhost:8000/v1 --set B --limit 3 --out runs/smoke`
6. Main runs (resume-safe, finished episodes are skipped):
   `python -m scripts.run_agent --model ... --set A --seeds 1 --parallel 3 --out runs/<model>/A`
   `python -m scripts.run_agent --model ... --set B --seeds 3 --parallel 3 --out runs/<model>/B`
7. Analysis: `python -c "from gil import analysis; import glob, json; print(json.dumps(analysis.summarize(analysis.load(glob.glob('runs/<model>/*/*.jsonl'))), indent=1))"`

Hosted fallback (no GPU): `--model gemini/gemma-4-31b-it` with GEMINI_API_KEY set (Ankith sets it with a ! command).
