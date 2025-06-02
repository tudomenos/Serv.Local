# Guia de Instalação e Execução Local no Windows 11

Este guia descreve os passos para configurar e executar o sistema de cadastro EAN localmente no seu computador com Windows 11, utilizando um banco de dados SQLite.

## Pré-requisitos

*   **Python 3:** Certifique-se de que tem o Python 3 instalado no seu sistema. Pode descarregá-lo em [python.org](https://www.python.org/downloads/). Durante a instalação, marque a opção "Add Python to PATH".
*   **Código Fonte:** Descarregue e descompacte o ficheiro `.zip` fornecido que contém o código fonte modificado do projeto.

## Passos de Instalação

1.  **Navegar para o Diretório do Projeto:**
    *   Abra o Explorador de Ficheiros e navegue até à pasta onde descompactou o projeto (por exemplo, `C:\Users\SeuUsuario\Downloads\EAN-projeto`).
    *   Clique com o botão direito do rato dentro da pasta (não em cima de um ficheiro) enquanto pressiona a tecla `Shift` e selecione "Abrir janela do PowerShell aqui" ou "Abrir Linha de Comandos aqui".

2.  **Criar um Ambiente Virtual:**
    *   No terminal (PowerShell ou Linha de Comandos) que abriu, execute o seguinte comando para criar um ambiente virtual chamado `venv`:
        ```bash
        python -m venv venv
        ```

3.  **Ativar o Ambiente Virtual:**
    *   **Para Linha de Comandos (cmd.exe):**
        ```bash
        .\venv\Scripts\activate
        ```
    *   **Para PowerShell:**
        ```bash
        .\venv\Scripts\Activate.ps1
        ```
        *   *Nota:* Se encontrar um erro no PowerShell relacionado com a política de execução de scripts, poderá ter de executar o seguinte comando (como Administrador) e tentar ativar novamente:
            ```powershell
            Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
            ```
    *   Após a ativação, deverá ver `(venv)` no início da linha do seu terminal.

4.  **Instalar as Dependências:**
    *   Com o ambiente virtual ativo, instale as bibliotecas Python necessárias executando:
        ```bash
        pip install -r requirements.txt
        ```
    *   **Resolução de Problemas (Erro ao instalar `pandas`/`numpy`):** Se encontrar um erro durante este passo mencionando a falta de um compilador C++ (como `cl.exe` ou `error: Microsoft Visual C++ 14.0 or greater is required`), siga estes passos:
        1.  **Atualize `pip`, `setuptools` e `wheel`:**
            ```bash
            python -m pip install --upgrade pip setuptools wheel
            ```
        2.  **Tente instalar `numpy` e `pandas` individualmente:**
            ```bash
            pip install numpy pandas
            ```
        3.  **Tente instalar o `requirements.txt` novamente:**
            ```bash
            pip install -r requirements.txt
            ```
        4.  **Se o erro persistir, instale as Ferramentas de Compilação do Microsoft C++:**
            *   Vá a [https://visualstudio.microsoft.com/pt-br/visual-studio-build-tools/](https://visualstudio.microsoft.com/pt-br/visual-studio-build-tools/)
            *   Descarregue e execute o instalador das "Build Tools for Visual Studio".
            *   Na secção "Cargas de Trabalho", selecione "Desenvolvimento para desktop com C++".
            *   Prossiga com a instalação.
            *   Após a instalação, reinicie o terminal, reative o ambiente virtual (`venv`) e tente novamente `pip install -r requirements.txt`.

## Executar a Aplicação

1.  **Iniciar o Servidor:**
    *   Certifique-se de que ainda está no diretório raiz do projeto (`EAN-projeto`) e que o ambiente virtual (`venv`) está ativo.
    *   Execute o seguinte comando para iniciar a aplicação Flask:
        ```bash
        python -m src.main
        ```
    *   O terminal deverá mostrar mensagens indicando que o servidor está a correr, incluindo algo como `Running on http://127.0.0.1:5000`.

2.  **Aceder à Aplicação:**
    *   Abra o seu navegador de internet (Chrome, Firefox, Edge, etc.).
    *   Navegue para o endereço: `http://127.0.0.1:5000`
    *   Deverá ver a página de login da aplicação.

3.  **Banco de Dados:**
    *   A aplicação utilizará um ficheiro de banco de dados SQLite chamado `produtos.db`. Este ficheiro será criado (se não existir) ou utilizado na pasta raiz do projeto (`EAN-projeto`).

4.  **Parar a Aplicação:**
    *   Para parar o servidor, volte à janela do terminal onde executou o comando `python -m src.main` e pressione `CTRL + C`.

## Credenciais Padrão

*   Se o banco de dados for criado pela primeira vez, um utilizador administrador padrão será criado:
    *   **Nome de utilizador:** `admin`
    *   **Senha:** `admin`
*   Recomenda-se alterar esta senha após o primeiro login.

Se encontrar algum problema, verifique se todos os passos foram seguidos corretamente, especialmente a ativação do ambiente virtual antes de instalar as dependências e executar a aplicação.
