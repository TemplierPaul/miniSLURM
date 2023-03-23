## Issues
- Proxy blocking curl requests
  - Solution: Add the following to your .bashrc file
```bash
alias curl='curl --noproxy localhost'
```