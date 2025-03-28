#!/bin/bash

# Abre um novo terminal e executa os comandos
open -a Terminal.app "$PWD" && \
osascript <<EOF
tell application "Terminal"
    do script "cd $PWD && source ~/miniconda3/etc/profile.d/conda.sh && conda activate bot-env && python main.py"
end tell
EOF
