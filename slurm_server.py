from flask import Flask, jsonify, request, g
import sqlite3

DATABASE = 'experiments.db'

app = Flask(__name__)

RUNNING = False
PAUSED = False

# check with tmux if something is running
def check_running():
    import subprocess
    global RUNNING
    # get the list of tmux sessions
    # command: tmux list-sessions -F '#{session_name}'
    try:
        sessions = subprocess.check_output(['tmux', 'ls']).decode('utf-8')
    except subprocess.CalledProcessError as e:
        sessions = e.output.decode('utf-8')
        RUNNING = False
        return
    sessions = sessions.splitlines()
    # if there is a session with the name starting with experiment-, then something is running
    if any([session.startswith('experiment-') for session in sessions]):
        RUNNING = True
    else:
        RUNNING = False

check_running()
    

# Connect to the database before each request
@app.before_request
def before_request():
    g.db = sqlite3.connect(DATABASE)

# Disconnect from the database after each request
@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

# Get a database cursor for the current request
def get_db():
    db = getattr(g, 'db', None)
    if db is None:
        db = g.db = sqlite3.connect(DATABASE)
    return db.cursor()

# Create the experiments table if it doesn't exist
def init_db():
    with app.app_context():
        cur = get_db()
        cur.execute('CREATE TABLE IF NOT EXISTS experiments (id INTEGER PRIMARY KEY, command TEXT, status TEXT)')

# Add a new experiment to the list
@app.route('/srun', methods=['POST'])
def add_experiment():
    # Only allow requests from localost
    # if request.remote_addr != '':
    #     return jsonify({'status': 'error', 'message': 'Only localhost is allowed to add experiments'})
    command = request.json.get('command', '')
    cur = get_db()
    # Get next id
    cur.execute('SELECT MAX(id) FROM experiments')
    # Get one 
    row = cur.fetchone()
    # If there's a row, get the first element of the row
    if row[0]:
        print(row)
        next_id = row[0] + 1
    # Otherwise, set the next id to 1
    else:
        next_id = 1
    command = command.strip().replace('$SLURM_JOB_ID', str(next_id))
    # Add the experiment to the database
    cur.execute('INSERT INTO experiments (command, status) VALUES (?, ?)', (command, 'waiting'))
    g.db.commit()

    # Check running

    job_status = "queued"
    if not RUNNING and not PAUSED:
        start_experiment()
        job_status = "started"
    return jsonify({'status': 'ok', "id": next_id, "job_status": job_status})

# Get the list of waiting experiments
@app.route('/squeue', methods=['GET'])
def get_queue():  # sourcery skip: merge-dict-assign, move-assign-in-block
    cur = get_db()
    if PAUSED:
        status = "Paused"
    elif RUNNING:
        status = "Running"
    else:
        status = "Waiting"
    experiments = {
        "waiting_nb": -1,
        "running_nb": -1,
        "Running": [],
        "Waiting": [],
        "status": status
    }

    # Count the number of waiting experiments
    cur.execute('SELECT COUNT(*) FROM experiments WHERE status="waiting"')
    experiments["waiting_nb"] = cur.fetchone()[0]
    # Count the number of running experiments
    cur.execute('SELECT COUNT(*) FROM experiments WHERE status="running"')
    experiments["running_nb"] = cur.fetchone()[0]
    
    # Check for --list and --listall options
    listall = request.args.get('listall', '')
    list_nb = request.args.get('list', '')

    # print(list_nb, type(list_nb), len(list_nb))

    # listall takes precedence over list, list all the experiments
    if listall == 'true':
        # Get all experiments with status "running"
        cur.execute('SELECT id, command, status FROM experiments WHERE status="running"')
        experiments["Running"] = [{'id': row[0], 'command': row[1], 'status':row[2]} for row in cur.fetchall()]
        # Get all experiments with status "waiting"
        cur.execute('SELECT id, command, status FROM experiments WHERE status="waiting"')
        experiments["Waiting"] = [{'id': row[0], 'command': row[1], 'status':row[2]} for row in cur.fetchall()]

    # With --list, only list the first experiments as specified by list_nb
    elif len(list_nb) > 0:
        list_nb = int(list_nb)
        # Get all experiments with status "running"
        cur.execute('SELECT id, command, status FROM experiments WHERE status="running" LIMIT ?', (list_nb,))
        experiments["Running"] = [{'id': row[0], 'command': row[1], 'status':row[2]} for row in cur.fetchall()]
        # Get all experiments with status "waiting"
        cur.execute('SELECT id, command, status FROM experiments WHERE status="waiting" LIMIT ?', (list_nb,))
        experiments["Waiting"] = [{'id': row[0], 'command': row[1], 'status':row[2]} for row in cur.fetchall()]

    return jsonify(experiments)

# Get the list of finished and cancelled experiments
@app.route('/sdone', methods=['GET'])
def get_done():  # sourcery skip: merge-dict-assign, move-assign-in-block
    cur = get_db()
    experiments = {}
    # Get all experiments with status "running"
    cur.execute('SELECT id, command, status FROM experiments WHERE status="finished"')
    experiments["Finished"] = [{'id': row[0], 'command': row[1], 'status':row[2]} for row in cur.fetchall()]
    # Get all experiments with status "waiting"
    cur.execute('SELECT id, command, status FROM experiments WHERE status="canceled"')
    experiments["Canceled"] = [{'id': row[0], 'command': row[1], 'status':row[2]} for row in cur.fetchall()]
    return jsonify(experiments)

# Cancel an experiment by id
@app.route('/scancel/<id>', methods=['DELETE'])
def cancel_experiment(id):
    if id == "all":
        # Cancel all experiments
        # Cancel waiting experiments
        ids = [row[0] for row in get_db().execute('SELECT id FROM experiments WHERE status="waiting"')]
        for id in ids:
            cancel_experiment(id)
        # Cancel running experiments
        ids = [row[0] for row in get_db().execute('SELECT id FROM experiments WHERE status="running"')]
        for id in ids:
            cancel_experiment(id)
        return jsonify({'status': 'ok'})

    cur = get_db()
    # Check if the experiment is running
    cur.execute('SELECT status FROM experiments WHERE id=?', (id,))
    status = cur.fetchone()
    if status and status[0] == 'running':
        # Kill the tmux session
        import subprocess
        subprocess.call(['tmux', 'kill-session', '-t', 'experiment-%d' % id])
    elif status and status[0] == 'finished':
        return jsonify({'status': 'error', 'message': 'Experiment already finished'})
    elif status and status[0] == 'canceled':
        return jsonify({'status': 'error', 'message': 'Experiment already canceled'})
    
    # Update the status of the experiment
    cur.execute('UPDATE experiments SET status="canceled" WHERE id=?', (id,))
    g.db.commit()
    return jsonify({'status': 'ok'})

# Mark an experiment as finished and start the next one
@app.route('/finished', methods=['POST'])
def finish_experiment():
    id = request.json.get('id', '')
    status = request.json.get('status', '')
    cur = get_db()
    # Update the status of the experiment
    cur.execute(f'UPDATE experiments SET status=? WHERE id=?', (status, id,))
    g.db.commit()
    global RUNNING
    RUNNING = False
    # If there's a next experiment, start it
    global PAUSED
    if not PAUSED:
        start_experiment()
    return jsonify({'status': 'ok'})

# Start the next experiment
@app.route('/start', methods=['GET'])
def start_experiment():
    global RUNNING, PAUSED
    if RUNNING:
        return jsonify({'status': 'error', 'message': 'Already running'})
    cur = get_db()
    cur.execute('SELECT id, command FROM experiments WHERE status="waiting" ORDER BY id ASC LIMIT 1')
    next_experiment = cur.fetchone()
    if next_experiment:
        next_id, next_command = next_experiment

        # Make the experiment call finished when it's done or failed
        next_command = f"({next_command}); exit_status=$?; source ~/.bashrc; finish {next_id} $exit_status" 

        # Start the command in a fresh tmux session
        import subprocess
        # subprocess.call(['tmux', 'new-session', '-d', '-s', 'experiment-%d' % next_id, next_command])
        
        cmd = f"tmux new-session -d -s experiment-{next_id} \"{next_command}\""
        subprocess.run(cmd, shell=True)
        print(f"Started experiment {next_id}: {cmd}")
        cur.execute('UPDATE experiments SET status="running" WHERE id=?', (next_id,))
        g.db.commit()
        RUNNING = True
        PAUSED = False
    return jsonify({'status': 'ok', "id": next_id, "command": next_command})

# Spause: don't automatically start the next experiment
@app.route('/spause', methods=['GET'])
def pause_experiment():
    global PAUSED
    PAUSED = True
    return jsonify({'status': 'ok'})

# Sresume: automatically start the next experiment
@app.route('/sresume', methods=['GET'])
def resume_experiment():
    global PAUSED
    PAUSED = False
    return jsonify({'status': 'ok'})

# Clear the database
@app.route('/clear', methods=['DELETE'])
def clear():
    cur = get_db()
    cur.execute('DELETE FROM experiments')
    g.db.commit()
    init_db()
    return jsonify({'status': 'ok'})

# clear command:
# curl -X DELETE http://localhost:5000/clear

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
