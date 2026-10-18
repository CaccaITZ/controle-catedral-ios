# Integração Holyrics — Prévia de Vídeo Catedral

Esta integração é uma etapa separada do aplicativo. Ela não altera as funções atuais do app nem modifica a fonte do OBS.

## Arquivos

- `01-modulo-previa-catedral.js`: módulo do Holyrics. Detecta o evento `displaying / any_video` e publica as informações do vídeo em uma variável global compartilhada do Holyrics.
- `02-api-server-previa-catedral.js`: exemplo de implementação para expor essa informação por uma ação personalizada do API Server.
- A chave global compartilhada é `@catedral#video_preview`.
- A ação HTTP será `GetCatedralVideoPreview`.

## Como funciona

1. O módulo observa cada vídeo exibido, sem aplicar o filtro do módulo OBS para nomes iniciados por `!`.
2. Obtém a configuração local do servidor de vídeo do Holyrics e calcula o token por arquivo com a mesma sequência do módulo Video Sync OBS+.
3. Armazena URL, caminho, nome e horário da atualização no estado global do Holyrics.
4. A ação personalizada do API Server devolve esses dados ao app.

## Importante antes do teste

- O arquivo usa o evento de módulo `displaying / any_video` e requer Holyrics 2.24 ou superior.
- A configuração local de vídeo deve conter `ip`, `port` e `token`, como no Video Sync OBS+.
- O IP configurado precisa ser alcançável pelo tablet. A URL é gerada com o IP da configuração, nunca com `localhost`.
- A função `request` do segundo arquivo é um exemplo completo. Se o API Server já tiver uma implementação personalizada, preserve-a e integre somente o caso `GetCatedralVideoPreview`; não sobrescreva as ações existentes.
- Esta primeira versão é para validação no computador. Só depois de comprovar no Holyrics que a ação retorna a URL correta, integraremos o app para consumir a ação, alterando exclusivamente a prévia do campo **Atual**.
- O aplicativo deverá continuar confirmando pelo `GetMediaPlayerInfo` se o vídeo está ativo e usando as informações de tempo do player para manter a sincronização.

## Teste esperado

Depois de instalar e ativar o módulo e integrar a ação personalizada, iniciar um vídeo deve fazer a ação `GetCatedralVideoPreview` retornar um objeto semelhante a:

```json
{
  "status": "ok",
  "data": {
    "available": true,
    "url": "http://IP:PORTA/get_video?path=...&token=...",
    "path": "...",
    "name": "...",
    "updated_at": 0
  }
}
```

O endereço e o token acima são exemplos de formato; o valor real é calculado pelo módulo durante a execução.
