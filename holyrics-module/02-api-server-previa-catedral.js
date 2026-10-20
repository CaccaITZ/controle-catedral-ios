/*
 * Ação personalizada do API Server — Prévia de Vídeo Catedral
 *
 * Integre este case à função request(action, headers, content, info)
 * do JavaScript personalizado do API Server do Holyrics.
 * NÃO substitua uma função request já existente por inteiro: preserve
 * os outros cases e o return true final.
 *
 * Ação consultada pelo app:
 * POST http://IP_DO_HOLYRICS:4545/api/GetCatedralVideoPreview?token=TOKEN
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
          message: "O módulo Prévia de Vídeo — Catedral ainda não publicou um vídeo."
        };
      }
      return {
        status: "ok",
        data: preview
      };
  }

  // Não bloqueia as ações padrão nem os demais endpoints personalizados.
  return true;
}
