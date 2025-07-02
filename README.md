# Sistema de Agendamento via WhatsApp

Este projeto implementa um chatbot de agendamento de consultas médicas (ou similar) acessível via WhatsApp, utilizando o framework Flask para a API e o Twilio para a integração com o WhatsApp. Ele permite que os usuários agendem, alterem e visualizem suas consultas de forma interativa através de mensagens.

## 🚀 Funcionalidades

O chatbot oferece as seguintes opções principais aos usuários via WhatsApp:

* **Agendar Nova Consulta**: Guia o usuário passo a passo para coletar todas as informações necessárias para um novo agendamento, como nome do paciente, email, telefone, motivo do agendamento, clínica, data, hora, etc.
* **Alterar Consulta Existente**: Permite que o usuário encontre um agendamento existente pelo CPF e modifique detalhes como a razão do agendamento, notas, data/hora, clínica, e profissional.
* **Listar Agendamentos de um Paciente**: Exibe todos os agendamentos associados a um determinado CPF, fornecendo um resumo detalhado de cada consulta.
* **Confirmação de Agendamentos Futuros**: Possui uma rota que, ao ser acionada, verifica os agendamentos para o dia seguinte e envia mensagens de confirmação automáticas via WhatsApp para os pacientes.

Além disso, a aplicação expõe rotas de API RESTful para manipulação de dados de pacientes e agendamentos:

* `GET /TOTAL-IP-case/patient`: Lista todos os pacientes (mockados).
* `GET /TOTAL-IP-case/patient/<string:OtherDocumentId>`: Busca um paciente por ID de documento (CPF).
* `GET /TOTAL-IP-case/patient/appointments/<string:OtherDocumentId>`: Lista agendamentos de um paciente por ID de documento.
* `GET /TOTAL-IP-case/appointments/<int:id>`: Busca um agendamento específico por ID.
* `GET /TOTAL-IP-case/patient/appointments/check_tomorrow_appointments`: Verifica e envia lembretes de agendamentos para o dia seguinte.
* `POST /TOTAL-IP-case/patient/appointments/create_appointment_by_api`: Cria um novo agendamento via API.
* `PUT /TOTAL-IP-case/patient/appointments/update_appointment_by_api/<int:appointment_id>`: Atualiza um agendamento existente via API.

## 🛠️ Tecnologias Utilizadas

* **Python**: Linguagem de programação principal.
* **Flask**: Microframework web para construção da API e do servidor.
* **Twilio**: Plataforma de comunicação em nuvem para integração com a API do WhatsApp.
* **`python-dotenv`**: (Sugerido para `.env`) Para gerenciar variáveis de ambiente (SID da conta Twilio, Token de Autenticação).
* **`requests`**: Biblioteca para fazer requisições HTTP para a API interna.
* **`datetime`**: Módulo para manipulação de datas e horas.
* **`re`**: Módulo para expressões regulares (usado para validação de entrada).

## ⚙️ Configuração e Instalação

Siga os passos abaixo para configurar e executar o projeto em sua máquina local.

### Pré-requisitos

Certifique-se de ter o Python 3.x instalado. Você pode verificar a versão com o comando:

```bash
python --version
````

### 1\. Clonar o Repositório

Primeiro, clone o repositório do seu projeto para sua máquina local e navegue até o diretório do projeto:

```bash
git clone <url>
cd <projeto>
```

### 2\. Criar e Ativar um Ambiente Virtual

É altamente recomendável usar um ambiente virtual para isolar as dependências do projeto. Isso evita conflitos com outros projetos Python.

```bash
python -m venv venv
```

Após criar o ambiente, ative-o:

  * **No Windows**:
    ```bash
    .\venv\Scripts\activate
    ```
  * **No macOS/Linux**:
    ```bash
    source venv/bin/activate
    ```

### 3\. Instalar as Dependências

Com o ambiente virtual ativado, instale as bibliotecas Python necessárias usando `pip`:

```bash
pip install Flask requests twilio python-dotenv
```

### 4\. Configurar Variáveis de Ambiente

Crie um arquivo chamado `.env` na raiz do seu projeto (no mesmo nível de `main.py` e `routes.py`). Este arquivo conterá suas credenciais do Twilio, que são essenciais para o bot funcionar. Você pode encontrar o `TWILIO_ACCOUNT_SID` e `TWILIO_AUTH_TOKEN` no [Console do Twilio](https://www.twilio.com/console).

```dotenv
TWILIO_ACCOUNT_SID='ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
TWILIO_AUTH_TOKEN='your_auth_token_here'
```

### 5\. Executar a Aplicação Flask

Com todas as dependências instaladas e os arquivos configurados, você pode iniciar o servidor Flask executando o arquivo `main.py`:

```bash
python main.py
```

Você verá uma mensagem no terminal indicando que o servidor Flask está rodando, geralmente em `http://localhost:5000`.

```
Iniciando servidor Flask em http://localhost:5000...
 * Serving Flask app 'routes'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on [http://127.0.0.1:5000](http://127.0.0.1:5000)
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: XXX-XXX-XXX
```

### 7\. Configurar Webhook do Twilio

Para que o Twilio envie as mensagens do WhatsApp para sua aplicação local, você precisará de uma ferramenta como `ngrok` para expor seu servidor local à internet.

1.  **Instale ngrok**: Se você ainda não tem o `ngrok`, baixe-o e siga as instruções de instalação no site oficial: [ngrok.com/download](https://ngrok.com/download).

2.  **Exponha sua porta Flask**: Abra um **novo terminal** (mantenha o terminal do Flask rodando) e execute o `ngrok`, direcionando-o para a porta 5000 onde seu Flask está rodando:

    ```bash
    ngrok http 5000
    ```

    O `ngrok` irá gerar uma URL pública temporária (ex: `https://xxxxxx.ngrok-free.app`). **Copie esta URL**.

    ```
    ngrok                                                                         (Ctrl+C to quit)

    Web Interface                 [http://127.0.0.1:4040](http://127.0.0.1:4040)
    Forwarding                    [https://xxxxxx.ngrok-free.app](https://xxxxxx.ngrok-free.app) -> http://localhost:5000
    Forwarding                    [http://xxxxxx.ngrok-free.app](http://xxxxxx.ngrok-free.app) -> http://localhost:5000

    Connections                   ttl     opn     rt1     rt5     p50     p90
                                  0       0       0.00    0.00    0.00    0.00
    ```

3.  **Configure o Webhook no Twilio**:

      * Acesse o [Console do Twilio](https://www.twilio.com/console) e faça login.
      * No menu lateral esquerdo, navegue até "Programmable Messaging" -\> "Settings" -\> "WhatsApp Sandbox Settings" (ou, se você já tiver um número de telefone Twilio habilitado para WhatsApp, vá para "Phone Numbers" -\> "Manage" -\> "Active numbers" e selecione seu número do WhatsApp).
      * Role para baixo até a seção "WHEN A MESSAGE COMES IN".
      * No campo de URL, insira a URL do `ngrok` que você copiou, seguida da rota da sua API de mensagem:
        `https://xxxxxx.ngrok-free.app/TOTAL-IP-case/message`
        (Substitua `xxxxxx.ngrok-free.app` pela sua URL real do ngrok).
      * Certifique-se de que o método HTTP esteja definido como `POST`.
      * Clique em "Save" (ou "Save Sandbox Settings").

## 🚀 Uso

Com o servidor Flask rodando e o webhook do Twilio configurado, você pode interagir com o bot diretamente do seu WhatsApp:

1.  **Envie uma mensagem de WhatsApp** para o seu número do Twilio (ou para o número do Sandbox do Twilio, se estiver usando o Sandbox).
2.  O bot responderá com o menu principal, e você poderá seguir os prompts para agendar, alterar ou listar consultas.

### Exemplos de Interação:

  * Para começar: Envie qualquer mensagem (ex: "Olá", "Oi", "Menu").
  * Para agendar uma nova consulta: Escolha a opção `1` quando o menu for apresentado.
  * Para alterar uma consulta existente: Escolha a opção `2` e siga as instruções.
  * Para listar seus agendamentos: Escolha a opção `3` e digite o seu CPF (Documento de Identificação).

-----

```
```
