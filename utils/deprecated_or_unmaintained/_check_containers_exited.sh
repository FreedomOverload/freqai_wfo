check_containers_exited() {
  # Get the status of all containers
  containers_status=$(sudo docker compose ps -a --format '{{.ID}}: {{.State}}')

  # Initialize variables
  all_exited=true

  # Loop through each container status
  while IFS= read -r line; do
    # Extract the state from the line
    state=$(echo "$line" | awk -F ': ' '{print $2}')

    # Check if the state is not 'exited'
    if [[ "$state" != "exited" ]]; then
      all_exited=false
      break
    fi
  done <<<"$containers_status"

  # Print the result
  if $all_exited; then
    return 0
  else
    return 1
  fi
}

echo "Waiting for all containers to exit ..."
  while true; do
    check_containers_exited
    if [[ $? -eq 0 ]]; then
      echo "All containers have exited"
      break
    else      
      sleep 10 # Wait for a few seconds before checking again
    fi
  done