#!/usr/bin/env bash

# Make srun but the command is the first argument
function srun() {
    response=$(curl -s --noproxy localhost -X POST -H "Content-Type: application/json" -d '{"command":"'"$1"'"}' http://localhost:5000/srun)
    # Parse the response to extract the experiment id
    id=$(echo "$response" | jq '.id')
    job_status=$(echo "$response" | jq '.job_status')
    # Remove "" from job status before and after
    job_status="${job_status%\"}"
    job_status="${job_status#\"}"
    # Check the response is json {"status": "ok"}, else print the error message
    if [[ $response == *"status"* ]]; then
        echo "Experiment $id $job_status"
    else
        echo $response
    fi
}

# Scancel
function scancel() {
    response=$(curl -s --noproxy localhost  -X DELETE http://localhost:5000/scancel/$1)
    # Check the response is json {"status": "ok"}, else print the error message
    if [[ $response == *"status"* ]]; then
        echo "Experiment $1 cancelled"
    else
        echo $response
    fi
}

# Spause
function spause() {
    response=$(curl -s --noproxy localhost -X GET http://localhost:5000/spause)
    # Check the response is json {"status": "ok"}, else print the error message
    if [[ $response == *"status"* ]]; then
        echo "Experiments paused"
    else
        echo $response
    fi
}

# Sresume
function sresume() {
    response=$(curl -s --noproxy localhost  -X GET http://localhost:5000/sresume)
    # Check the response is json {"status": "ok"}, else print the error message
    if [[ $response == *"status"* ]]; then
        echo "Experiments resumed"
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
    # Check for command line options
    if [[ "$1" == "--list" ]]; then
        # Check for a limit
        if [[ -z "$2" ]]; then
            # No limit specified, use default
            limit=10
            echo "No limit specified, using default limit of $limit"
        else
            # Limit specified, use it
            limit="$2"
        fi
        # List commands for running and waiting jobs up to specified limit
        response=$(curl -s --noproxy localhost -s http://localhost:5000/squeue?list="$2")
    elif [[ "$1" == "--listall" ]]; then
        # List commands for all running and waiting jobs
        response=$(curl -s --noproxy localhost -s http://localhost:5000/squeue?listall=true)
    else
        # Return counts of running and waiting jobs
        response=$(curl -s --noproxy localhost -s http://localhost:5000/squeue)
    fi
    # echo $response

    # Parse the JSON response and extract the "running_nb" and "waiting_nb" numbers
    running_nb=$(echo "$response" | jq '.running_nb')
    waiting_nb=$(echo "$response" | jq '.waiting_nb')

    # Get status
    status=$(echo "$response" | jq '.status')
    echo "miniSLURM status: $status"

    # Print the length of each array
    echo "Running: $running_nb"
    echo "Waiting: $waiting_nb"

    # Parse the JSON response and extract the "Running" and "Waiting" arrays
    running=$(echo "$response" | jq '.Running')
    waiting=$(echo "$response" | jq '.Waiting')

    # echo $running
    # echo $waiting

    # If there are no running or waiting jobs, exit function
    if [ "$running_nb" -eq 0 ] && [ "$waiting_nb" -eq 0 ]; then
        return
    fi

    # Add --list or --listall argument to print all the jobs
    if [ "$1" == "--list" ] || [ "$1" == "--listall" ]; then
    
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
    fi

}

function sdone() {
    # Make the request and save the JSON response
    response=$(curl -s --noproxy localhost  -s http://localhost:5000/sdone)

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

function sstart(){
    response =$(curl -s --noproxy localhost  http://localhost:5000/start)
     # Check the response is json {"status": "ok"}, else print the error message
    if [[ $response == *"status"* ]]; then
        echo "Experiment $id $job_status"
    else
        echo $response
    fi

}


# Scance
function sfinished() {
      curl -s --noproxy localhost -X POST -H "Content-Type: application/json" -d "{\"id\": \"$1\", \"status\": \"finished\"}" http://localhost:5000/finished
}

function finish {
    echo "Experiment $1 finished"
    if [ $? -eq 0 ]; then
        status="finished"
    else
        status="failure"
    fi
    echo "Experiment $1 finished with status $status"
    curl -s --noproxy localhost -X POST -H "Content-Type: application/json" -d "{\"id\": \"$1\", \"status\": \"$status\"}" http://localhost:5000/finished
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
export -f spause
export -f sresume
