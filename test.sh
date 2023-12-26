#!/usr/bin/env bash
source aliases.sh

srun "echo 'Hello World!'; sleep 10"

srun "echo 'Hello Again!'; sleep 10"

srun "echo 'Hello from the other side'; sleep 10"
