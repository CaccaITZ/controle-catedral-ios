/*
 * Prévia de vídeo — Catedral
 * Holyrics 2.24+
 *
 * Publica no estado global do Holyrics o endereço reproduzível do vídeo
 * que começou a ser exibido. A URL é calculada com a mesma lógica do
 * módulo oficial/comunitário Video Sync OBS+, usando a configuração local
 * de vídeo do Holyrics. Não altera nem controla o OBS.
 */

var CATEDRAL_VIDEO_PREVIEW_KEY = "@catedral#video_preview";

function info() {
  return {
    id: "catedral_video_preview",
    name: "Prévia de Vídeo — Catedral",
    description: "Compartilha com o aplicativo Catedral o endereço do vídeo exibido no Holyrics, inclusive vídeos cujo nome começa com !.",
    min_version: "2.24.0",
    available_in_main_window: true,
    available_in_bible_window: false
  };
}

function readPluginVideoSettings() {
  var candidates = ["~$.plugin_system_settings.txt", ".plugin_system_settings.txt"];

  for (var i = 0; i < candidates.length; i++) {
    try {
      var raw = h.readFileAsText(candidates[i]);
      var parsed = JSON.parse(raw);
      if (parsed && parsed.ip && parsed.port && parsed.token) {
        return parsed;
      }
    } catch (e) {
      // Try the next supported location.
    }
  }

  return null;
}

function createCatedralVideoUrl(settings, fullPath) {
  // Reproduce o algoritmo usado pelo módulo Video Sync OBS+.
  var token = h.sha256(fullPath + "#" + settings.token);
  token = h.base64Encode(token);
  token = token.replaceAll("[^a-zA-Z0-9]", "");
  token = token.substring(0, Math.min(20, token.length));

  var host = String(settings.ip);
  var port = String(settings.port);
  var portPart = port === "80" ? "" : ":" + port;

  return "http://" + host + portPart +
    "/get_video?path=" + encodeURIComponent(fullPath) +
    "&token=" + token;
}

function publishCatedralVideoPreview(obj) {
  var fullPath = String(obj && obj.file_fullname || "").trim();

  if (!fullPath) {
    h.setGlobal(CATEDRAL_VIDEO_PREVIEW_KEY, {
      available: false,
      message: "O Holyrics não forneceu o caminho completo do vídeo.",
      updated_at: new Date().getTime()
    });
    return;
  }

  var settings = readPluginVideoSettings();
  if (!settings) {
    h.setGlobal(CATEDRAL_VIDEO_PREVIEW_KEY, {
      available: false,
      path: fullPath,
      message: "Não foi possível ler a configuração de vídeo do Holyrics. Verifique se o módulo Video Sync OBS+ está configurado.",
      updated_at: new Date().getTime()
    });
    return;
  }

  try {
    var url = createCatedralVideoUrl(settings, fullPath);
    var normalized = fullPath.replace(/\\/g, "/");
    var fileName = normalized.substring(normalized.lastIndexOf("/") + 1);

    h.setGlobal(CATEDRAL_VIDEO_PREVIEW_KEY, {
      available: true,
      url: url,
      path: fullPath,
      name: fileName,
      updated_at: new Date().getTime()
    });
  } catch (e) {
    h.setGlobal(CATEDRAL_VIDEO_PREVIEW_KEY, {
      available: false,
      path: fullPath,
      message: "Falha ao gerar o endereço de reprodução do vídeo.",
      updated_at: new Date().getTime()
    });
  }
}

function startup(module) {
  h.setGlobal(CATEDRAL_VIDEO_PREVIEW_KEY, {
    available: false,
    message: "Aguardando o próximo vídeo exibido pelo Holyrics.",
    updated_at: new Date().getTime()
  });
}

function triggers(module) {
  return [{
    when: "displaying",
    item: "any_video",
    action: function (obj) {
      publishCatedralVideoPreview(obj);
    }
  }];
}
