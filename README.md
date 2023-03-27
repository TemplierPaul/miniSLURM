# miniSLURM
Python server and database for managing jobs on a remote machine using SLURM-like commands.
Code based on ChatGPT interactions.

## Architecture
A Flask server is running in a tmux session on the remote machine. The server is listening for requests from the client. The client is a bash script that sends requests to the server and parses the response. The server is connected to a SQLite database that stores the jobs in the queue to have persistent storage.

When a job is started, a new tmux session is opened to run the command. When it ends, it triggers a curl request to the server to finish the job. The server then updates the database and starts the next job in the queue. This allows the server to run jobs consecutively without having to be restarted.

## Commands
- `srun 'python script.py'` - Submit a job to the queue and start if not paused
- `sstart` - Start running jobs in the queue, unpauses the server
- `spause` - Pause the server from running new jobs, does not cancel current jobs
- `sresume` - Resume the server from running new jobs
- `squeue` - Count the number of jobs in the queue
  - `squeue --listall` - List all jobs in the queue
  - `squeue --list 5` - List the first 5 in the queue
- `scancel <id>` - Cancel a job in the queue
  - `scancel all` - Cancel all jobs in the queue
- `sdone` - List all jobs that have finished running
- `sfinished <id>` - Finish a job 
- `finish <id> <status>` - Finish a job with a specific status

## Setup
Start the server in a tmux session:
```bash
tmux new-session -d -s miniSLURM 'python miniSLURM/slurm_server.py'
```

Add the aliases to your .bashrc file:
```bash
source /path/to/miniSLURM/aliases.sh
```

## Usage
```bash
srun 'python script.py'
squeue # List all jobs in the queue
sstart # Start running jobs in the queue
```

<!-- ## Issues
- Proxy blocking curl requests
  - Solution: Add the following to your .bashrc file
```bash
alias curl='curl --noproxy localhost'
``` -->

## TODO
- [x] Check if a job is running when doing `sstart`
- [x] Add a `spause` command to stop the server from running new jobs after the current job finishes