# Security and trust boundaries

flyfishHep is alpha software for reviewed local calculations. It is **not a sandbox**.

- `--allow-exec` authorizes arbitrary Python from the selected project. Review every input and import first. Use OS/container isolation and a network-denied environment for untrusted code.
- The runner reduces inherited environment variables but cannot revoke filesystem, process or network permissions. Do not expose credentials or sensitive research to an untrusted calculation.
- Timeouts stop the direct child, not an entire process tree. They are not CPU, memory or disk quotas.
- Hashes detect ordinary accidental changes; a writer able to replace the complete evidence tree can forge it. Receipts are neither signatures nor trusted timestamps.
- The input manifest does not establish dependency completeness. The verifier checks declared numerical criteria, not their physical meaning.

Keep sensitive disclosure details and exploit-bearing data out of public issues. Use GitHub's **Report a vulnerability** option on this repository when available; otherwise open a minimal issue requesting a private reporting channel without including secrets or an exploit. There is no guaranteed response-time SLA for this alpha project.
