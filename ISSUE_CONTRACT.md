# Issue Contract — `token_saver`

## Pain
Repeated context burns tokens; need pure_pointer / externalize.

## Claim
pure_pointer reduces large payload to path+hash style envelope.

## Proof
```bash
python3 job-app/helix/proofs/proof_token_saver.py
```

## Done when
Proof exits 0. Architecture (strand/integrity/helix) is **not** a substitute for this proof.

## Anti-claim
Not a full agent runtime.
