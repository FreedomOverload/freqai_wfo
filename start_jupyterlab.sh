# Set up python environment
sudo apt-get update -y && sudo apt-get install -y python3-venv git python3-pip
python3 -m venv .venv
source .venv/bin/activate
which python
pip install -r ./utils/requirements.txt
# pip-review --local --auto

# Install docker
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing..."
    curl -fsSL get.docker.com | sh
else
    echo "Docker is already installed."
fi

# cloudlare warp client setup (optional)
# curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
# echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list
# sudo apt-get install cloudflare-warp

# enable sudo without password so docker command can work inside jupyterlab
echo "$(whoami) ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/$(whoami)
jupyter lab --no-browser --ip=0.0.0.0
