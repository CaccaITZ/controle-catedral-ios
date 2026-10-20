/*
 * Prévia de vídeo — Catedral
 * Holyrics 2.24+
 *
 * Detecta o vídeo exibido no Holyrics e publica sua URL no estado global.
 * A URL aponta para o serviço HTTP de vídeo configurado no Plugin do Holyrics.
 * O módulo não controla nem precisa de uma conexão com o OBS.
 */

var CATEDRAL_VIDEO_PREVIEW_KEY = "@catedral#video_preview";

function info() {
  return {
    id: "catedral_video_preview",
    name: "Prévia de Vídeo — Catedral",
    description: "Compartilha com o aplicativo Catedral o endereço do vídeo exibido no Holyrics.",
    min_version: "2.24.0",
    available_in_main_window: true,
    available_in_bible_window: false
  };
}

/*
 * O host pode ser definido nas configurações deste módulo.
 * Se ficar vazio, usa o IP informado na configuração do serviço de vídeo.
 * Para testar no navegador do próprio PC, pode-se usar 127.0.0.1.
 * Para celulares/tablets, use o IP da rede local do PC que executa Holyrics.
 */
function settings() {
  return [
    {
      type: "title",
      label: "Endereço para reprodução da prévia"
    },
    {
      id: "video_url_host",
      name: "IP/host do servidor de vídeo",
      description: "Endereço que o aparelho que reproduz a prévia consegue acessar. Use 127.0.0.1 somente no próprio PC; para outros aparelhos, use o IP de rede do computador Holyrics. Deixe vazio para usar o IP da configuração do serviço de vídeo.",
      type: "string",
      default_value: ""
    }
  ];
}

function readPluginVideoSettings() {
  var candidates = ["~$.plugin_system_settings.txt", ".plugin_system_settings.txt"];

  for (var i = 0; i < candidates.length; i++) {
    try {
      var raw = h.readFileAsText(candidates[i]);
      var parsed = JSON.parse(raw);
      if (parsed && parsed.port && parsed.token) {
        return parsed;
      }
    } catch (e) {
      // Tenta o próximo local suportado.
    }
  }

  return null;
}

function createCatedralVideoUrl(settings, fullPath, module) {
  var token = h.sha256(fullPath + "#" + settings.token);
  token = h.base64Encode(token);
  token = token.replace(/[^a-zA-Z0-9]/g, "");
  token = token.substring(0, Math.min(20, token.length));

  var configuredHost = String(
    module && module.settings && module.settings.video_url_host || ""
  ).trim();
  var host = configuredHost || String(settings.ip || "").trim();

  if (!host) {
    throw new Error("O host do servidor de vídeo não está configurado.");
  }

  var port = String(settings.port);
  var portPart = port === "80" ? "" : ":" + port;

  return "http://" + host + portPart +
    "/get_video?path=" + encodeURIComponent(fullPath) +
    "&token=" + token;
}

function publishCatedralVideoPreview(obj, module) {
  var fullPath = String(obj && obj.file_fullname || "").trim();

  if (!fullPath) {
    h.setGlobal(CATEDRAL_VIDEO_PREVIEW_KEY, {
      available: false,
      message: "O Holyrics não forneceu o caminho completo do vídeo.",
      updated_at: new Date().getTime()
    });
    return;
  }

  var videoSettings = readPluginVideoSettings();
  if (!videoSettings) {
    h.setGlobal(CATEDRAL_VIDEO_PREVIEW_KEY, {
      available: false,
      path: fullPath,
      message: "Não foi possível ler a configuração do serviço HTTP de vídeo do Plugin do Holyrics. Verifique se o serviço está configurado.",
      updated_at: new Date().getTime()
    });
    return;
  }

  try {
    var url = createCatedralVideoUrl(videoSettings, fullPath, module);
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
      message: String(e && e.message || "Falha ao gerar o endereço de reprodução do vídeo."),
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
      publishCatedralVideoPreview(obj, module);
    }
  }];
}
