clear
source .venv/bin/activate
CONFIG=user_data/configs/config_AwesomeMacdFreqAi_livetrade.json
LEVERAGE=20
gateiobot_live() {
    sudo docker compose run --name gateiobot_live --env FT_LEVERAGE=$LEVERAGE freqtrade_freqai_livetrade trade --config $CONFIG
}

gateiobot_dry() {
    sudo docker compose run --name gateiobot_dry --env FT_LEVERAGE=$LEVERAGE freqtrade_freqai_livetrade --config $CONFIG --dry-run
}

gateiobot_dry