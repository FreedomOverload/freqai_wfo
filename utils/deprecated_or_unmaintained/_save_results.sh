mkdir -p baseline_results
for container in $(sudo docker compose ps -a --format "{{.Names}}"); do
    FILE=baseline_results/$container.txt
    sudo docker logs $container | sed 's/\x1b\[[0-9;]*m//g' > $FILE
    echo $FILE
    # echo -e "\n\n" >>$FILE
    # sed -i '/freqtrade/d' $FILE
    # sed -i '/INFO/d' $FILE
    # sed -i '/WARNING/d' $FILE
    # sed -i '/nan/d' $FILE
done