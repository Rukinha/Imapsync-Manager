# IMAPSync Manager

Aplicação desktop (Python + PyQt6) para gerenciar migrações de e-mail em massa
com o `imapsync`, substituindo os scripts Bash usados atualmente pela equipe
de suporte da Plenus.

## Pré-requisitos

- Python 3.12+
- `imapsync` instalado e acessível no `PATH` do sistema
  (`sudo apt install imapsync` no Debian/Ubuntu, ou instalação manual)
- Dependências Python: `pip install -r requirements.txt`

## Executando

```bash
python main.py
```

## Estrutura

```
imapsync-manager/
│
├── main.py                        # Ponto de entrada
├── ui/
│   ├── main_window.ui              # Tela principal (Qt Designer)
│   └── profile_dialog.ui           # Cadastro/edição de perfil de servidor
├── controllers/
│   ├── main_controller.py          # Liga a main_window.ui à lógica
│   ├── migration_manager.py        # Orquestra a fila de migrações (paralelismo)
│   ├── profile_dialog_controller.py
│   ├── profile_manager_dialog.py   # Lista/CRUD de perfis
│   └── account_dialog.py           # Diálogo para adicionar 1 conta manualmente
├── models/
│   ├── profile.py                  # Perfil de servidor IMAP (origem/destino)
│   └── account.py                  # Conta de e-mail + status de migração
├── services/
│   ├── profiles.py                 # Persistência de perfis em config/profiles.json
│   ├── imapsync.py                 # Monta comando + executa o binário via QProcess
│   ├── error_translator.py         # Traduz/classifica erros comuns do imapsync
│   ├── settings.py                 # Preferências persistidas (operador, toggles)
│   └── power.py                    # Desligamento do sistema (Linux/Windows/macOS)
├── config/
│   ├── profiles.json               # Perfis cadastrados (criado automaticamente)
│   └── settings.json               # Preferências do operador (criado automaticamente)
├── logs/                           # Logs exportados
└── resources/                      # Ícones, etc.
```

## Fluxo de uso

1. **Identifique-se**: preencha o campo *Operador responsável* no topo da tela.
   Esse nome fica salvo (`config/settings.json`) e passa a assinar todas as
   linhas do log, junto com data/hora — importante para auditoria de quem
   fez cada migração.
2. **Cadastrar servidores**: botão *Gerenciar Perfis* → *Novo* (nome, host, porta,
   SSL, tipo de autenticação, timeout, prefixo IMAP, cor, observações).
3. **Testar conexão**: dentro do cadastro de perfil, ou na tela principal com
   *Testar Conexões* (testa origem e destino selecionados no topo).
4. **Selecionar Origem/Destino** nos combos da tela principal.
5. **Adicionar contas**: manualmente (*Adicionar Conta*) ou em lote
   (*Importar CSV*), aceitando dois formatos de arquivo (`.csv` ou `.txt`):
   - **Com cabeçalho** (vírgula ou `;`): `email,senha_origem,senha_destino`
   - **Sem cabeçalho**, padrão pedido pela equipe (`;` como separador):
     `conta;senha-origem;senha-destino`
   O parser detecta automaticamente qual dos dois formatos está sendo usado.
6. **Mostrar/ocultar senhas**: checkbox *Mostrar senhas na listagem* alterna
   entre exibir as senhas em texto plano ou mascaradas (•••) na tabela.
   Preferência salva entre sessões.
7. **Agendar início** (opcional): marque *Agendar início para:*, escolha
   data/hora, e clique em *Iniciar* — a migração dispara sozinha no horário
   marcado (o programa precisa ficar aberto). *Cancelar* desfaz o agendamento.
8. **Executar migração**: *Iniciar* dispara até 4 migrações simultâneas
   (`MigrationManager.max_parallel`), cada uma em um processo `imapsync`
   separado via `QProcess` — a interface não trava.
9. **Reconexão automática**: com *Reconectar automaticamente em caso de queda*
   marcado (padrão), contas que falharem por motivo de rede/conexão (timeout,
   conexão recusada, DNS, SSL, etc. — não falha de senha) voltam sozinhas
   para a fila após 5 minutos, até 3 tentativas. O status da conta mostra
   "aguardando nova tentativa" nesse intervalo.
10. **Acompanhar progresso**: tabela de contas (status/progresso/velocidade/
    motivo do erro traduzido), linhas coloridas por situação (vermelho = erro,
    amarelo = aguardando nova tentativa, verde = concluído), aba de log geral
    e aba de log da conta selecionada, barra de progresso geral.
11. **Pausar/Cancelar**: *Pausar* deixa as execuções atuais terminarem sem
    iniciar novas; *Cancelar* mata os processos em andamento, limpa a fila e
    cancela qualquer agendamento pendente.
12. **Desligar ao final** (opcional): marque *Desligar o computador ao final
    da migração* — ao concluir tudo, o programa pede confirmação e desliga a
    máquina em 30 segundos (dá tempo de cancelar). Funciona em Linux
    (`systemctl poweroff`), Windows e macOS.
13. **Exportar logs**: botão *Exportar Logs* salva o log geral em `logs/`.

### Tradução de erros

A saída do `imapsync` é longa e em inglês. O módulo
`services/error_translator.py` reconhece os erros mais comuns (timeout,
conexão recusada, DNS, SSL, login/senha inválidos, quota excedida, etc.) e
gera uma frase curta em português, exibida na coluna *Motivo* da tabela e
destacada no log geral — sem precisar garimpar linha por linha. O log
completo em inglês continua disponível na aba de log da conta, para
diagnósticos mais profundos.

## Parâmetros padrão do imapsync

Definidos em `services/imapsync.py` (`DEFAULT_FLAGS`):

```
--automap --subscribe --syncinternaldates --skipsize --nofoldersizes --noauthmd5
```

Uma tela de **Configurações → Parâmetros do imapsync** (ação já presente no menu,
handler ainda a implementar) é o próximo ponto natural para tornar essas flags
editáveis pela equipe sem mexer em código.

## Próximos passos sugeridos

- Persistir contas e histórico de migrações em JSON/SQLite (hoje ficam em memória
  durante a sessão).
- Implementar a tela de edição de `DEFAULT_FLAGS` (Configurações Globais).
- Progresso geral ponderado por bytes/mensagens reais, não só por contas concluídas.
- Retomar migrações após fechar/abrir o programa (persistir fila + status).
- Empacotamento com PyInstaller para distribuição interna.
# Imapsync-Manager

## Instalacao rapida no Ubuntu / WSL

No Ubuntu ou em uma distribuicao Ubuntu no WSL, o instalador baixa o projeto do GitHub, instala Python, `imapsync` e as dependencias graficas, cria o ambiente virtual e deixa um comando de execucao pronto:

```bash
curl -fsSL https://raw.githubusercontent.com/Rukinha/Imapsync-Manager/main/install-imapsync-manager.sh | bash
```

Ao final, abra pelo menu de aplicativos ou execute:

```bash
~/.local/bin/imapsync-manager
```

Para atualizar uma instalacao, rode novamente o mesmo comando. O instalador atualiza o repositorio sem apagar `config/profiles.json` e as preferencias locais. Em WSL e necessario usar WSLg (Windows 11) ou um servidor grafico compativel para que a janela PyQt seja exibida.

### Recursos de acompanhamento

- A aba **Erros** reune somente falhas, mostra a quantidade total e permite filtrar por conta ou copiar o resultado para encaminhar ao suporte.
- Eventos de erro no **Log Geral** sao marcados com `ERRO`; a linha da conta permanece destacada em vermelho e exibe o motivo resumido.
- A nova tentativa automatica pode ocorrer imediatamente, em 30 segundos, 1, 5 ou 15 minutos. A escolha e salva para a proxima sessao.
- Em **Arquivo > Exportar Perfis de Servidor...**, salve os perfis em JSON para transferi-los a outro computador. Esse arquivo contem dados de conexao dos servidores; armazene-o de forma segura.
