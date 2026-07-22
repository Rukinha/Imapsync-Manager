#!/bin/bash
# ==============================================================================
# Instalação do Imapsync Manager para WSL / Ubuntu
# Execução: ./install-imapsync-manager.sh
# ==============================================================================

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

REPO_URL="https://github.com/Rukinha/Imapsync-Manager.git"
TARGET_DIR="Imapsync-Manager"

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}     Instalador do Imapsync Manager (Linux/WSL)     ${NC}"
echo -e "${CYAN}====================================================${NC}"

# 1. Dependências do sistema (incluindo pacotes para PyQt6 no Linux/WSLg)
echo -e "\n${YELLOW}[1/4] Verificando e instalando dependências do sistema (apt)...${NC}"
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip imapsync desktop-file-utils \
                    libgl1-mesa-glx libegl1-mesa libxkbcommon-x11-0 libdbus-1-3 libxcb-cursor0

# 2. Clonar ou Atualizar o Repositório do Git
echo -e "\n${YELLOW}[2/4] Baixando repositório do Git...${NC}"

if [ -d "$TARGET_DIR/.git" ]; then
    echo -e "${CYAN}A pasta '$TARGET_DIR' já existe. Atualizando código via git pull...${NC}"
    cd "$TARGET_DIR"
    git pull origin main || git pull origin master
else
    echo -e "${CYAN}Clonando repositório em ./$TARGET_DIR ...${NC}"
    git clone "$REPO_URL" "$TARGET_DIR"
    cd "$TARGET_DIR"
fi

# 3. Configurar ambiente virtual Python (venv)
echo -e "\n${YELLOW}[3/4] Criando e configurando ambiente virtual Python (venv)...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Atualiza o pip dentro do ambiente virtual
./venv/bin/pip install --upgrade pip

# 4. Instalar dependências Python
echo -e "\n${YELLOW}[4/4] Instalando dependências do Python...${NC}"
if [ -f "requirements.txt" ]; then
    echo -e "${CYAN}Instalando pacotes listados no requirements.txt...${NC}"
    ./venv/bin/pip install -r requirements.txt
else
    echo -e "${CYAN}requirements.txt não encontrado. Instalando PyQt6>=6.6.0 por padrão...${NC}"
    ./venv/bin/pip install "PyQt6>=6.6.0"
fi

# Voltar para o diretório raiz onde o script foi chamado
cd ..

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}      ✅ Instalação Concluída com Sucesso!          ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "\nPara executar a aplicação, rode os comandos abaixo:\n"
echo -e "  ${CYAN}cd Imapsync-Manager${NC}"
echo -e "  ${CYAN}source venv/bin/activate${NC}"
echo -e "  ${CYAN}python3 main.py${NC}"
echo -e "\nOu em uma única linha:"
echo -e "  ${CYAN}cd Imapsync-Manager && source venv/bin/activate && python3 main.py${NC}\n"
