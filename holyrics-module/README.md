# Prévia de Vídeo — receptor no PC do Holyrics

Este módulo publica a URL autenticada do vídeo no próprio PC que executa o Holyrics. O app consulta esse PC usando o IP que o usuário informa dentro do aplicativo. **O módulo não precisa saber o IP do tablet/celular**, então um mesmo APK funciona em aparelhos diferentes.

## Arquivos

- `01-modulo-previa-catedral.js`: detecta vídeos no Holyrics, calcula a URL autenticada usando a mesma lógica do módulo Video Sync OBS+ e envia a URL para `127.0.0.1:8766`.
- `../tools/servidor-index-pc-teste.ps1`: receptor HTTP local para Windows. Deve ser executado no PC do Holyrics durante o teste.
- `../www/index-pc-teste.html`: página de teste para validar o fluxo antes de compilar o APK.

## Fluxo

1. O módulo detecta o vídeo exibido e gera a URL autenticada.
2. Faz POST para `http://127.0.0.1:8766/api/video-preview` no próprio PC do Holyrics.
3. O servidor local guarda a URL mais recente e disponibiliza `/__receiver/video-preview/latest` pela rede.
4. O app consulta `http://IP_DO_PC_HOLYRICS:8766/__receiver/video-preview/latest`, usando o IP que o usuário já configura para conectar ao Holyrics.
5. O app reproduz o vídeo recebido no campo **Atual** e continua utilizando a API Holyrics na porta `4545` para sincronização.

## Configuração

No módulo:
- Não é necessário informar IP de dispositivo.
- Mantenha o registro de atividade ativado durante os testes.

No app:
- Informe o IP do PC que executa o Holyrics.
- O app usa a porta `4545` para a API Holyrics e a porta `8766` para a URL da prévia.

## Testar antes de compilar o APK

1. Copie `servidor-index-pc-teste.ps1` e `index-pc-teste.html` para a mesma pasta no PC do Holyrics.
2. Execute o script nesse computador e mantenha o PowerShell aberto.
3. No módulo, exiba um vídeo no Holyrics. O PowerShell deve registrar `URL recebida do módulo`.
4. No PC do OBS ou em outro dispositivo da mesma rede, acesse o endereço de teste exibido pelo PowerShell, por exemplo `http://192.168.10.178:8766/index-pc-teste.html`. A página de teste deverá reproduzir o vídeo em **Atual**.
5. No app Android, informe o IP do PC do Holyrics. Não configure IP algum do tablet/celular no módulo.

Se o navegador ou app não alcançar o receptor, permita conexões TCP de entrada na porta `8766` no Firewall do Windows. Os dispositivos devem estar na mesma rede ou em redes com rota entre si.
