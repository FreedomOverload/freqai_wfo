clear
bash ./tools/_prepare_environment.sh && source .venv/bin/activate
TIMERANGE="20180101-20241211"

listpair() {
  local EXCHANGE=$1
  local CONFIG=$2
  sudo docker stop strategy_update && sudo docker rm strategy_update
  sudo docker compose run --name "freqtrade_numba-listpair-$EXCHANGE" freqtrade_numba list-pairs --exchange $EXCHANGE --config $CONFIG --all --quote USDT USD --print-json
}

gateio_listpair() {
  local EXCHANGE=gateio
  local CONFIG=user_data/configs/backtest_$EXCHANGE-futures_NFIx5.json
  listpair $EXCHANGE $CONFIG
}

bash ./tools/_clean_up.sh
bash ./tools/_cloudflared_warp.sh

gateio_listpair
