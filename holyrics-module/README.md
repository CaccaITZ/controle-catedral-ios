# Prévia de Vídeo — Controle Catedral

Esta integração publica a URL do vídeo exibido no Holyrics para que o aplicativo possa consultá-la pela ação personalizada `GetCatedralVideoPreview`.

## Arquivos

- `01-modulo-previa-catedral.js`: detecta o vídeo exibido, calcula a URL autenticada do serviço HTTP de vídeo e publica o estado compartilhado.
- `02-api-server-previa-catedral.js`: exemplo da ação personalizada `GetCatedralVideoPreview` que devolve a URL ao aplicativo.

## Configuração no Holyrics

1. O serviço HTTP de vídeo do Plugin do Holyrics precisa estar configurado e disponível. O módulo usa a porta e o token dessa configuração para montar a URL `/get_video`; ele não inicia um servidor HTTP por conta própria.
2. Instale e ative `01-modulo-previa-catedral.js` na janela de Módulos do Holyrics.
3. Nas configurações do módulo **Prévia de Vídeo — Catedral**, configure **IP/host do servidor de vídeo**:
   - Para testar o HTML no navegador do mesmo PC, pode usar `127.0.0.1`, desde que o serviço de vídeo aceite conexões locais.
   - Para celulares/tablets ou outros computadores, use o IP de rede do computador que disponibiliza o serviço de vídeo, acessível por esses aparelhos. Não use `127.0.0.1` nesses dispositivos.
   - Se deixar o campo vazio, o módulo usará o IP da configuração do serviço de vídeo.
4. No JavaScript personalizado do **API Server** do Holyrics, integre o caso `GetCatedralVideoPreview` fornecido em `02-api-server-previa-catedral.js`. Se já existir uma função `request(action, headers, content, info)`, preserve os demais casos e acrescente somente o caso indicado.
5. Confirme que o API Server está ativo na porta usada pelo app (neste projeto, `4545`) e que o token tem permissão para consultar a ação.

## Fluxo

1. O módulo detecta um vídeo exibido no Holyrics.
2. Gera a URL autenticada usando o token e a porta da configuração do serviço HTTP de vídeo, aplicando o IP/host configurado no próprio módulo quando preenchido.
3. Guarda URL, caminho, nome e horário no estado global do Holyrics.
4. A ação personalizada `GetCatedralVideoPreview` expõe esse estado pela API.
5. O app consulta a ação e usa `GetMediaPlayerInfo` para sincronizar a reprodução.

## Importante

- O IP configurado para a URL de vídeo é o endereço que o aparelho cliente precisa alcançar. `127.0.0.1` só aponta para o próprio dispositivo que abre a URL.
- O módulo não precisa de um PC com OBS para detectar e publicar o vídeo. Entretanto, a reprodução remota requer que o serviço HTTP de vídeo do Plugin do Holyrics esteja disponível na rede.
- Não é necessário iniciar PowerShell nem um receptor auxiliar para esta arquitetura.
