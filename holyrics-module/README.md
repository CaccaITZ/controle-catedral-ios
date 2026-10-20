# Prévia de Vídeo — Controle Catedral

Esta integração publica a URL autenticada do vídeo no próprio Holyrics. Cada instalação do Controle Catedral consulta o API Server do Holyrics usando o IP informado no aplicativo. **O módulo não precisa saber o IP de nenhum tablet ou celular**, e não é necessário iniciar PowerShell, OBS ou um servidor auxiliar.

## Arquivos

- `01-modulo-previa-catedral.js`: detecta o vídeo exibido, gera a URL autenticada e a publica no estado compartilhado do Holyrics.
- `02-api-server-previa-catedral.js`: exemplo da ação personalizada `GetCatedralVideoPreview` que devolve essa URL aos aplicativos.

## Fluxo

1. O módulo detecta um vídeo e calcula a URL `/get_video` autenticada, usando as configurações do serviço de vídeo do Holyrics.
2. O módulo guarda a URL, o nome e o horário no estado compartilhado do Holyrics.
3. A ação personalizada `GetCatedralVideoPreview` expõe esse estado pela API do Holyrics.
4. Cada app consulta essa ação e reproduz o vídeo no campo **Atual**, sincronizando o tempo por `GetMediaPlayerInfo`.

Todos os aparelhos podem consultar a mesma URL publicada. O módulo não aponta para aparelhos individuais.

## Configuração única em cada computador que executa o Holyrics

1. Instale e ative `01-modulo-previa-catedral.js` na janela de Módulos do Holyrics.
2. No JavaScript personalizado do **API Server** do Holyrics, integre o caso `GetCatedralVideoPreview` fornecido em `02-api-server-previa-catedral.js`. Se já existir uma função `request(action, headers, content, info)`, não a substitua por completo: acrescente somente o `case` indicado e preserve os outros casos e o `return true` final.
3. Confirme que o API Server está ativo na porta usada pela instalação (neste projeto, `4545`) e que o token tem permissão para consultar as ações.

Essa configuração é feita no computador do Holyrics, uma vez por unidade — não em cada aparelho.

## No aplicativo

Informe o IP do computador que executa o Holyrics. O app usa a porta `4545` para consultar tanto a API padrão quanto a ação `GetCatedralVideoPreview`. Não há IP de tablet, porta `8766`, serviço PowerShell ou servidor auxiliar.

## Requisitos de rede

Os dispositivos precisam conseguir alcançar o computador do Holyrics pela rede. A URL `/get_video` publicada precisa usar um IP/porta de vídeo que também seja acessível pelos aparelhos. Em outra unidade/cidade, o app deve apontar para o computador do Holyrics daquela unidade, e essa instalação deve ter o módulo e a ação personalizada configurados.

## Manutenção

O receptor temporário em PowerShell e a página de teste anteriores foram descartados desta arquitetura. Não é necessário iniciar um comando de shell para usar o app.
