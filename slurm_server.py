from flask import Flask, jsonify, request, g
import sqlite3

DATABASE = 'experiments.db'

app = Flask(__name__)

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
    if request.remote_addr != '':
        return jsonify({'status': 'error', 'message': 'Only localhost is allowed to add experiments'})
    command = request.json.get('command', '')
    cur = get_db()
    # Get next id
    cur.execute('SELECT MAX(id) FROM experiments')
    next_id = cur.fetchone()[0] + 1 if cur.fetchone()[0] else 1
    command = command.strip().replace('$SLURM_JOB_ID', str(next_id))
    # Add the experiment to the database
    cur.execute('INSERT INTO experiments (command, status) VALUES (?, ?)', (command, 'waiting'))
    g.db.commit()
    return jsonify({'status': 'ok'})

# Get the list of waiting experiments
@app.route('/squeue', methods=['GET'])
def get_queue():  # sourcery skip: merge-dict-assign, move-assign-in-block
    cur = get_db()
    experiments = {}
    # Get all experiments with status "running"
    cur.execute('SELECT id, command, status FROM experiments WHERE status="running"')
    experiments["Running"] = [{'id': row[0], 'command': row[1], 'status':row[2]} for row in cur.fetchall()]
    # Get all experiments with status "waiting"
    cur.execute('SELECT id, command, status FROM experiments WHERE status="waiting"')
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
@app.route('/scancel/<int:id>', methods=['DELETE'])
def cancel_experiment(id):
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
@app.route('/finished/<int:id>', methods=['PUT'])
def finish_experiment(id):
    cur = get_db()
    cur.execute('UPDATE experiments SET status="finished" WHERE id=?', (id,))
    g.db.commit()
    # If there's a next experiment, start it
    start_experiment()
    return jsonify({'status': 'ok'})

# Start the next experiment
@app.route('/start', methods=['GET'])
def start_experiment():
    cur = get_db()
    cur.execute('SELECT id, command FROM experiments WHERE status="waiting" ORDER BY id ASC LIMIT 1')
    next_experiment = cur.fetchone()
    if next_experiment:
        next_id, next_command = next_experiment
        print("Running experiment %d: %s" % (next_id, next_command))

        # Make the experiment call finished when it's done or failed
        next_command += ' && curl -X PUT http://localhost:5000/finished/%d' % next_id
        next_command += ' || curl -X PUT http://localhost:5000/finished/%d' % next_id

        # Start the command in a fresh tmux session
        import subprocess
        subprocess.call(['tmux', 'new-session', '-d', '-s', 'experiment-%d' % next_id, next_command])
        cur.execute('UPDATE experiments SET status="running" WHERE id=?', (next_id,))
        g.db.commit()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
