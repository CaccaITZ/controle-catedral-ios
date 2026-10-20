# Prévia de Vídeo — envio direto ao Controle Catedral

Este módulo envia a URL autenticada do vídeo diretamente ao aplicativo Controle Catedral. **Não consulta o OBS e não exige que o OBS esteja aberto.**

## Arquivos

- `01-modulo-previa-catedral.js`: módulo que detecta vídeos exibidos no Holyrics, gera a URL com o algoritmo do módulo Video Sync OBS+ e envia essa URL por HTTP POST ao aplicativo.
- A antiga integração `02-api-server-previa-catedral.js` não faz parte deste fluxo. O aplicativo não consulta uma ação personalizada para buscar a URL: ele recebe a requisição enviada pelo módulo.

## Fluxo

1. Ao exibir um vídeo, o módulo lê a configuração do serviço de vídeo do Holyrics em `.plugin_system_settings.txt`.
2. Usa o caminho completo do vídeo e o segredo dessa configuração para calcular o token, seguindo o algoritmo do Video Sync OBS+.
3. Envia um POST para `http://IP_DO_DISPOSITIVO:8766/api/video-preview`, com `url`, `path`, `name` e `updated_at`.
4. O Controle Catedral recebe a URL no receptor HTTP nativo e reproduz o vídeo no campo **Atual**.
5. A API do Holyrics continua sendo utilizada separadamente para sincronizar o tempo do vídeo e controlar a apresentação.

## Configuração do módulo

Na configuração do módulo, defina:

- **IP do dispositivo Controle Catedral:** o IP local do tablet/celular que executa o aplicativo.
- **Porta receptora HTTP:** `8766`.

A configuração de IP/porta da API do Holyrics é independente da porta do receptor de vídeo. Neste projeto, a API foi configurada em `4545`; o receptor de URL do aplicativo utiliza `8766`.

Se a política de requisições permitidas do Holyrics bloquear o envio, inclua o IP do dispositivo Controle Catedral em **Arquivo → Configurações → Avançado → JavaScript → Configurações → Requisições permitidas**.

## Teste do índice no PC antes do APK

1. Baixe `www/index-pc-teste.html` e `tools/servidor-index-pc-teste.ps1) para a mesma pasta.
2. Execute o script com Windows PowerShell. Ele abre o índice de teste e fornece localmente o endpoint HTTP que simula o receptor nativo.
3. Na configuração do módulo no Holyrics, use IP `127.0.0.1` e porta `8766`. Como o Holyrics e o servidor de teste estão no mesmo PC, a requisição chegará ao teste local.
4. Inicie um vídeo no Holyrics. O servidor mostrará no PowerShell que recebeu a URL; a página de teste deverá reproduzi-la em **Atual**.

Mantenha a janela do PowerShell aberta durante o teste. A porta `4545` é usada pelo proxy local apenas para consultar a API do Holyrics; a URL autenticada do vídeo chega por POST em `8766`.

## Observações

- O teste de navegador utiliza um servidor PowerShell local porque uma página HTML aberta sozinha não consegue receber conexões HTTP de entrada.
- O endpoint nativo `/api/video-preview` é implementado para Android no build do aplicativo. O código principal e as funções de letras, playlist, próximo slide e modo texto não dependem do OBS.
- O módulo envia a URL mais recente quando um vídeo é exibido. A disponibilidade do vídeo no dispositivo ainda depende de o IP/porta do serviço de vídeo do Holyrics serem acessíveis pela rede local.
