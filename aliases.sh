#!/usr/bin/env bash

# Make srun but the command is the first argument
function srun() {
    curl --noproxy localhost -X POST -H "Content-Type: application/json" -d '{"command":"'"$1"'"}' http://localhost:5000/srun
}

# Scancel
function scancel() {
    response=$(curl --noproxy localhost  -X DELETE http://localhost:5000/scancel/$1)
    # Check the response is json {"status": "ok"}, else print the error message
    if [[ $response == *"status"* ]]; then
        echo "Experiment $1 cancelled"
    else
        echo $response
    fi
}


# Define a function to print a row of the table
print_row () {
    local status="$1"
    local id="$2"
    local command="$3"
    printf "| %-8s | %-5s | %-30s \n" "$status" "$id" "$command"
}

function squeue() {
    # Make the request and save the JSON response
    response=$(curl --noproxy localhost  -s http://localhost:5000/squeue)
    # echo $response

    # Parse the JSON response and extract the "Running" and "Waiting" arrays
    running=$(echo "$response" | jq '.Running')
    waiting=$(echo "$response" | jq '.Waiting')

    # Print the header of the table
    printf "+----------+-------+--------------------------------+\n"
    printf "| Status   | ID    | Command                         \n"
    printf "+----------+-------+--------------------------------+\n"

    # Print the rows of the table for the "Running" experiments
    # Iterate on the list of experiments

    for row in $(echo "${running}" | jq -r '.[] | @base64'); do
        _jq() {
            echo ${row} | base64 --decode | jq -r ${1}
        }

        # Extract the fields from the JSON response
        id=$(_jq '.id')
        command=$(_jq '.command')

        # Print the row
        print_row "Running" "$id" "$command"
    done

    printf "+----------+-------+--------------------------------+\n"

    # Print the rows of the table for the "Waiting" experiments
    # Iterate on the list of experiments

    for row in $(echo "${waiting}" | jq -r '.[] | @base64'); do
        _jq() {
            echo ${row} | base64 --decode | jq -r ${1}
        }

        # Extract the fields from the JSON response
        id=$(_jq '.id')
        command=$(_jq '.command')

        # Print the row
        print_row "Waiting" "$id" "$command"
    done

    # Print the footer of the table
    printf "+----------+-------+--------------------------------+\n"

}

function sdone() {
    # Make the request and save the JSON response
    response=$(curl --noproxy localhost  -s http://localhost:5000/sdone)

    # Parse the JSON response and extract the "Running" and "Waiting" arrays
    finished=$(echo "$response" | jq '.Finished')
    canceled=$(echo "$response" | jq '.Canceled')

    # Print the header of the table
    printf "+----------+-------+--------------------------------+\n"
    printf "| Status   | ID    | Command                         \n"
    printf "+----------+-------+--------------------------------+\n"

    # Print the rows of the table for the "Running" experiments
    # Iterate on the list of experiments

    for row in $(echo "${finished}" | jq -r '.[] | @base64'); do
        _jq() {
            echo ${row} | base64 --decode | jq -r ${1}
        }

        # Extract the fields from the JSON response
        id=$(_jq '.id')
        command=$(_jq '.command')

        # Print the row
        print_row "Finished" "$id" "$command"
    done

    printf "+----------+-------+--------------------------------+\n"

    # Print the rows of the table for the "Waiting" experiments
    # Iterate on the list of experiments

    for row in $(echo "${canceled}" | jq -r '.[] | @base64'); do
        _jq() {
            echo ${row} | base64 --decode | jq -r ${1}
        }

        # Extract the fields from the JSON response
        id=$(_jq '.id')
        command=$(_jq '.command')

        # Print the row
        print_row "Canceled" "$id" "$command"
    done

    # Print the footer of the table
    printf "+----------+-------+--------------------------------+\n"

}


alias sstart='curl --noproxy localhost  http://localhost:5000/start'

# Scance
function sfinished() {
      curl --noproxy localhost -X POST -H "Content-Type: application/json" -d "{\"id\": \"$1\", \"status\": \"finished\"}" http://localhost:5000/finished
}

function finish {
    echo "Experiment $1 finished"
    if [ $? -eq 0 ]; then
        status="finished"
    else
        status="failure"
    fi
    echo "Experiment $1 finished with status $status"
    curl --noproxy localhost -X POST -H "Content-Type: application/json" -d "{\"id\": \"$1\", \"status\": \"$status\"}" http://localhost:5000/finished
}

export -f finish

# Export squeue
export -f squeue
export -f print_row
alias q='watch -x bash -c squeue'
export -f sdone
export -f srun
export -f scancel
export -f sfinished

