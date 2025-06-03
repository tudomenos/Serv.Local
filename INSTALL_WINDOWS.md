# Instruções de Instalação e Execução no Windows 11

Este documento contém instruções detalhadas para instalar e executar o Sistema de Cadastro de Produtos por EAN localmente no Windows 11.

## Requisitos

- Windows 11
- Python 3.8 ou superior
- Acesso à Internet (para instalação de dependências)

## Passos para Instalação

### 1. Preparar o Ambiente

1. **Descompacte o arquivo** do projeto em uma pasta de sua preferência (ex: `C:\System\sistema`).

2. **Abra o Prompt de Comando (CMD) ou PowerShell** como administrador:
   - Pesquise por "cmd" ou "powershell" no menu Iniciar
   - Clique com o botão direito e selecione "Executar como administrador"

3. **Navegue até a pasta do projeto**:
   ```
   cd C:\caminho\para\pasta\do\projeto
   ```

### 2. Criar e Ativar o Ambiente Virtual

1. **Crie um ambiente virtual Python**:
   ```
   python -m venv venv
   ```

2. **Ative o ambiente virtual**:
   - No PowerShell:
     ```
     .\venv\Scripts\Activate.ps1
     ```
   - No CMD:
     ```
     .\venv\Scripts\activate
     ```

### 3. Instalar Dependências

1. **Atualize o pip, setuptools e wheel** (importante para evitar erros de compilação):
   ```
   python -m pip install --upgrade pip setuptools wheel
   ```

2. **Instale numpy e pandas primeiro** (para evitar erros de compilação):
   ```
   pip install numpy pandas
   ```

3. **Instale as demais dependências**:
   ```
   pip install -r requirements.txt
   ```

### 4. Configurar Variáveis de Ambiente para API do Mercado Livre

Para que a busca de produtos por EAN funcione corretamente, é necessário configurar as credenciais do Mercado Livre:

1. **No PowerShell**, configure as variáveis de ambiente:
   ```powershell
   $env:MERCADO_LIVRE_CLIENT_ID = "7401826900082952"
   $env:ML_CLIENT_SECRET = "AtsQ0fxExmiYTE8eE0bAWi1Q1yOL26Jv"
   ```

2. **No CMD**, configure as variáveis de ambiente:
   ```cmd
   set MERCADO_LIVRE_CLIENT_ID=7401826900082952
   set ML_CLIENT_SECRET=AtsQ0fxExmiYTE8eE0bAWi1Q1yOL26Jv
   ```

**Importante**: Estas variáveis de ambiente são válidas apenas para a sessão atual do terminal. Se fechar o terminal, precisará configurá-las novamente.

## Executando a Aplicação

1. **Com o ambiente virtual ativado**, execute o comando:
   ```
   python -m src.main
   ```

2. **Acesse a aplicação** no navegador:
   ```
   http://127.0.0.1:5000
   ```

3. **Faça login** com as credenciais padrão:
   - Usuário: `admin`
   - Senha: `admin`

## Resolução de Problemas

### Erro: "Address already in use"

Se receber o erro `Address already in use Port 5000 is in use by another program`, significa que a porta 5000 já está sendo usada por outro programa. Você pode:

1. **Encontrar e encerrar o processo que está usando a porta 5000**:
   - Abra o CMD ou PowerShell como administrador
   - Execute: `netstat -ano | findstr ":5000"`
   - Identifique o PID (último número na linha)
   - Execute: `taskkill /PID [número_do_PID] /F`

2. **Ou usar uma porta diferente**:
   ```
   python -m src.main --port 5001
   ```
   E acesse: `http://127.0.0.1:5001`

### Erro ao Instalar Dependências

Se encontrar erros ao instalar as dependências, especialmente relacionados à compilação de pacotes como numpy ou pandas:

1. **Certifique-se de ter executado os comandos na ordem correta**:
   - Primeiro atualizar pip, setuptools e wheel
   - Depois instalar numpy e pandas separadamente
   - Por fim, instalar as demais dependências

2. **Se os erros persistirem**, pode ser necessário instalar as "Ferramentas de Compilação do Microsoft C++":
   - Acesse: https://visualstudio.microsoft.com/pt-br/visual-cpp-build-tools/
   - Baixe e instale o "Build Tools for Visual Studio"
   - Na instalação, selecione "Desenvolvimento para desktop com C++"
   - Após a instalação, reinicie o terminal e tente novamente

## Funcionalidades Principais

- **Login/Registro**: Sistema de autenticação de usuários
- **Busca por EAN**: Consulta produtos pelo código EAN no Mercado Livre
- **Cadastro de Produtos**: Adicione produtos à lista com informações detalhadas
- **Envio de Listas**: Envie listas de produtos para validação por responsáveis
- **Painel Administrativo**: Visualize e valide listas enviadas
- **Exportação para Excel**: Exporte dados para planilhas Excel

## Suporte

Para suporte adicional, entre em contato com o administrador do sistema.
