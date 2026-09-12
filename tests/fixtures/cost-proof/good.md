## Cost proof

The deepseek lane now marks its prefix; DeepSeek caches it.

```cost-proof
before: 1685 calls, 5,666,503 input tokens, $0.1177 / 15 min

after: 166 calls, 17,786,972 input tokens, marked prefix, cached=23808 on a 24008-token call

command: kubectl logs -n llm job/proof && kubectl logs -n llm job/proof2
```
