clear
# unmaintained file
get_all_pairlist() {
    local EXCHANGE=$1
    local CONFIG=$2
    sudo docker compose run --rm freqtrade_numba list-pairs --config $CONFIG --exchange $EXCHANGE --quote USDT --print-list # --all
}

# high risk of losing balance
get_all_pairlist mexc user_data/configs_secret/config_secret_mexc.json
