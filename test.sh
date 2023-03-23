#!/usr/bin/env bash
source aliases.sh

srun 'echo Hello World!; sleep 5'

srun 'echo Hello Again!; sleep 5'

srun 'echo Hello from the other side; sleep 5'
