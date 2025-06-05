# Sistema Multiusuário de Cadastro de Produtos por EAN (Adaptado para Windows com SQLite)

Este é um sistema web para cadastro de produtos por código EAN (código de barras), com persistência em banco de dados **SQLite**, suporte a múltiplos usuários e painel central para visualização das listas enviadas.

**Nota:** Esta versão foi ajustada para usar SQLite, conforme o funcionamento original descrito em alguns arquivos. O banco de dados (`produtos.db`) será criado automaticamente na pasta principal da aplicação.

## Funcionalidades

- Sistema de login e cadastro de usuários
- Busca automática de informações por EAN (requer internet para EANs não cadastrados localmente)
- Persistência de dados em banco de dados SQLite (`produtos.db`)
- Priorização de busca local antes de consulta externa
- Autopreenchimento de campos para produtos já cadastrados
- Soma automática de quantidade para produtos repetidos
- Envio de listas para painel central (requer PIN de responsável)
- Painel administrativo para visualização e validação de todas as listas enviadas
- Exportação para Excel no formato EAN, DESCRIÇÃO, QUANTIDADE

## Requisitos

- Windows 10 ou 11
- Python 3.6 ou superior (instalado e adicionado ao PATH)
- Acesso à internet (para instalação de dependências e busca de EAN)
- PowerShell (para execução do script de inicialização)

## Instalação e Execução no Windows

1.  **Extraia os arquivos:** Descompacte o arquivo `.zip` fornecido em uma pasta de sua preferência.
2.  **Abra o PowerShell:** Navegue até a pasta onde você extraiu os arquivos. Clique com o botão direito do mouse dentro da pasta (em um espaço vazio) segurando a tecla `Shift` e selecione "Abrir janela do PowerShell aqui" ou "Abrir no Terminal Windows".
3.  **Permitir Execução de Scripts (se necessário):** Se for a primeira vez executando scripts PowerShell baixados, pode precisar ajustar a política de execução. Execute:
    ```powershell
    Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
    ```
    Confirme com \'S\' (Sim) ou \'T\' (Sim para Todos).
4.  **Execute o Script de Inicialização:** No terminal PowerShell, execute:
    ```powershell
    .\iniciar_sistema.ps1
    ```
5.  **Aguarde a Instalação:** O script irá:
    *   Verificar Python.
    *   Criar/ativar um ambiente virtual (`.venv`).
    *   Instalar as dependências listadas em `requirements.txt`.
    *   Iniciar o servidor web Flask.
    *   Na primeira execução, criará o arquivo de banco de dados `produtos.db` e as tabelas necessárias na pasta principal.
6.  **Acesse a Aplicação:** Após a mensagem "Iniciando a aplicação Flask...", abra seu navegador e acesse:
    [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Uso

(Conforme descrito no README original, lembrando que o usuário admin padrão é `admin`/`admin`)

## Estrutura do Projeto (Principais Arquivos)

- `iniciar_sistema.ps1`: Script PowerShell para iniciar a aplicação no Windows.
- `requirements.txt`: Lista de dependências Python (sem `psycopg2-binary`).
- `produtos.db`: Arquivo do banco de dados SQLite (criado automaticamente na pasta principal).
- `src/main.py`: Código principal da aplicação Flask (usa SQLite).
- `src/templates/`: Arquivos HTML.
- `README_WINDOWS.md`: Este arquivo de instruções.

## Observações

- O banco de dados (`produtos.db`) é criado automaticamente na pasta principal na primeira execução.
- Um usuário administrador (`admin`/`admin`) é criado automaticamente na primeira execução.
- Para interromper a aplicação, volte à janela do PowerShell e pressione `Ctrl + C`.
- A funcionalidade de busca de EAN online requer conexão com a internet.

