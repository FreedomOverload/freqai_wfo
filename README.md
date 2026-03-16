# A simple Jupyter work flow for FreqAI Walk-Forward Optimization

An attempt to automates the complex process of running multiple FreqAI backtests plus training a secondary Meta-Model (e.g., CatBoostRegressor).

The model only use regular OHCL data provided by the exchange (ie: Binance) so unlikely to make long term profits. (No on-chain data was intergrated)

<img src="/preview/p0.png" width="50%">

# Structure
- notebook.ipynb: interactive Jupyter notebook
- notebook_code.py: backend logic handling Docker orchestration and meta model training.
- notebook_config.json: stores the parameters set via the interactive UI.
- user_data/: Contains Freqtrade-specific configurations (config_freqai.json), strategies, and data.
- output/: store backtest results (CSV).
- utils/: Helper scripts for environment setup and data handling.
- start_jupyterlab.sh: Shell script to setup the environment and everything.

# Usage
- Launch start_jupyterlab.sh in Ubuntu 22.04, wait for link to access JupyterLab via your browser
- Step 0: Configure Parameters (To be explained)
  
  <img src="/preview/p1.png" width="50%">
  
- Step 1: Train base model on past data (ie: 20250101-20260101). This will also force a download QHCL data from 2018 to now.

  <img src="/preview/p2.png" width="50%">
  
- Step 2: Train meta model on present data (ie: 20260101-20260301), and backtest again to show actual performance

  <img src="/preview/p3.png" width="50%">

# FAQ
- To be added.
