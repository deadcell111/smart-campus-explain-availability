# Prompt comparison

## Offline structural comparison (no model involved)

| Property | p1 minimal | p2 constrained | p3 constrained + guard |
|---|---|---|---|
| limits model to supplied facts | no | yes | yes |
| forbids changing the status | no | yes | yes |
| length limit (<= 2 sentences) | no | yes | yes |
| demands JSON output shape | no | yes | yes |
| treats input as data (injection guard) | no | no | yes |
| forbids booking/confirmation claims | no | no | yes |
| defines every reasonCode | no | no | yes |
| contains a worked example | no | no | yes |
| characters (tokens ~ chars/4, estimate) | 49 (~12) | 298 (~74) | 912 (~228) |
| features satisfied (of 8) | 0 | 4 | 8 |

## Live comparison (factual agreement and consistency)

**NOT RUN** - ANTHROPIC_API_KEY is not set. No model outputs exist for these prompts, so no claim about factual agreement or consistency is made. To run: `pip install anthropic; export ANTHROPIC_API_KEY=...; python3 -I tools/compare_prompts.py 3`.
