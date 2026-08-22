# p2p 隔离环境 - source /home/wff/p2p/env.sh
export P2P=/home/wff/p2p
export PATH="$P2P/bin:$P2P/pi/node_modules/.bin:$P2P/venv/bin:$PATH"
alias pi='env HOME="$P2P/home" pi'
alias p2p-pi='env HOME="$P2P/home" pi'
p2p() { env HOME="$P2P/home" pi "$@"; }
echo "[p2p] PATH -> p2p/bin, p2p/pi/.bin, p2p/venv | pi 命令已隔离(HOME=$P2P/home)"
