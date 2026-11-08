# Ghosts in the Loop

Harness, frozen prompts and results for **"Ghosts in the Loop: When Local Coding Agents Install Packages That Do Not Exist"**
(Kaggle Gemma 4 Developer Agent, paper track, Nov 2026).

Coding agents don't just suggest packages, they install them. We put Gemma 4 models (E4B and 31B) inside a minimal
coding-agent loop that really runs `pip` and `npm` in a sandbox, against the live PyPI and npm registries, and record every
install of a name that does not exist ("ghost"), what the agent does after the install fails, and what an install-time
guard in shadow mode would have blocked.

**Headline.** Scale fixes the model's own inventions, not the user's: 31B almost never invents a package name by itself
(1 of 75 time-anchored tasks vs 17 for E4B; 0 of 60 misspellings vs 9), but when the task names a library that does not
exist it still tries to install it in 85% of episodes (E4B: 88%). An existence check at the install boundary catches every
attempt and wrongly blocked none of 1,152 real installs.

## Layout
- `gil/` agent loop, Docker sandbox, install extraction, tiered shadow guard, analysis (Wilson intervals)
- `prompts/` Set A (300 natural) and Set B (100 stress) prompts, frozen and hashed before any run; `names_check.json` lists the 5 Set B names excluded because they already exist
- `scripts/` `run_agent` (resume-safe), `verify_names`, `report`, `figures`, `release`
- `third_party/` vendored, MIT-licensed code from [ghostcheck](https://github.com/Ankith-m1006/ghostcheck) and [Gatekeeper](https://github.com/Ankith-m1006/gatekeeper)
- `results/` aggregate reports per model and the paper's figures
- `RUN.md` how to reproduce on one GPU

## Responsible release
Raw trajectories are not published. In `results/`, package names that the models invented on their own are replaced by
a salted SHA-256 prefix (`h:...`), because a name an agent repeatedly tries to install is exactly what an attacker would
register. Names we invented ourselves for the Set B prompts are kept. Registry security teams can request the plain list.

## License
Apache 2.0 (harness). Vendored code in `third_party/` keeps its MIT license.
