/*
 * Integração API Server — Prévia de Vídeo Catedral
 *
 * Adicione este caso à implementação JavaScript personalizada do API Server
 * do Holyrics. Se já existir uma função request(action, headers, content, info),
 * NÃO substitua a função inteira: copie apenas o bloco case e mantenha todos
 * os casos existentes e o return true final.
 *
 * Endpoint esperado pelo aplicativo:
 * POST http://IP:PORTA/api/GetCatedralVideoPreview?token=TOKEN
 * Content-Type: application/json
 * Body: {}
 */

function request(action, headers, content, info) {
  switch (String(action || "").toLowerCase()) {
    case "getcatedralvideopreview":
      var preview = h.getGlobal("@catedral#video_preview", null);
      if (preview == null) {
        preview = {
          available: false,
          message: "Módulo Prévia de Vídeo — Catedral ainda não publicou um vídeo."
        };
      }
      return {
        status: "ok",
        data: preview
      };
  }

  // Mantém o processamento padrão para todas as outras ações da API.
  return true;
}
