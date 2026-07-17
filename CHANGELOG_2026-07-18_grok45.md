# grok2api local update 2026-07-18

## Why
Clients request `grok-4.5`, but local grok2api registry only exposed 4.20/4.3 names.
With only basic-pool accounts, many super/heavy models also disappear from `/v1/models`.

## Changes
1. Register compatibility models:
   - `grok-4.5`, `grok-4.5-console`, `grok-4.5-low/medium/high` (console.x.ai → `grok-4.3`)
   - `grok-4.5-fast/auto/expert` (prefer_best chat aliases)
2. Normalize common spellings: `grok4.5`, `grok_4.5`, `grok-4-5`, `grok-4.5-latest`
3. Map console payload model ids for the new 4.5 names.
