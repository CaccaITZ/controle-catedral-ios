/*
 * Prévia de Vídeo — Catedral (envio direto ao aplicativo)
 * Holyrics 2.24+
 *
 * Ao exibir um vídeo, calcula a URL autenticada e publica no receptor local
 * do PC que executa o Holyrics. O aplicativo consulta essa URL usando o IP
 * do PC do Holyrics informado pelo usuário; o IP do tablet/celular não importa.
 * Não consulta nem controla o OBS.
 */

var CATEDRAL_VIDEO_PREVIEW_MODULE_ID = "catedral_video_preview_push";

function info() {
  return {
    id: CATEDRAL_VIDEO_PREVIEW_MODULE_ID,
    name: "Prévia de Vídeo — Envio ao Controle Catedral",
    description: "Publica a URL autenticada no receptor local do PC do Holyrics para o Controle Catedral consultar pela rede. Não depende do OBS.",
    // A URL é enviada ao serviço local no mesmo PC que executa o Holyrics.
    allowed_requests: [
      "http://127.0.0.1:8766/api/video-preview"
    ],
    min_version: "2.24.0",
    available_in_main_window: true,
    available_in_bible_window: false
  };
}

function settings() {
  return [
    {
      type: "label",
      name: "Publica a URL no PC do Holyrics para o app consultar. Não é necessário usar o OBS para esta função."
    },
    {
      type: "label",
      name: "A URL é enviada ao serviço local deste PC. No aplicativo, informe apenas o IP deste computador."
    },
    {
      id: "log",
      name: "Registrar atividade no log",
      type: "boolean",
      default_value: true
    }
  ];
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
      // Tenta o próximo caminho de configuração.
    }
  }
  return null;
}

function createCatedralVideoUrl(settings, fullPath) {
  // Mantém exatamente a sequência de hash/base64 usada pelo módulo Video Sync OBS+.
  var token = h.sha256(fullPath + "#" + settings.token);
  token = h.base64Encode(token);
  token = token.replaceAll("[^a-zA-Z0-9]", "");
  token = token.substring(0, Math.min(20, token.length));

  // O receptor é outro dispositivo; portanto, nunca utilizar localhost aqui.
  var host = String(settings.ip);
  var port = String(settings.port);
  var portPart = port === "80" ? "" : ":" + port;

  return "http://" + host + portPart +
    "/get_video?path=" + encodeURIComponent(fullPath) +
    "&token=" + token;
}

function enviarUrlAoAplicativo(module, payload) {
  // O receptor fica no mesmo PC do Holyrics: nenhum IP do aparelho é necessário.
  var endpoint = "http://127.0.0.1:8766/api/video-preview";

  try {
    // A API documentada do Holyrics para requisições diretas é module.apiRequest.
    var response = module.apiRequest(endpoint, {
      type: "POST",
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify(payload),
      timeout: 3000,
      response_data_type: "string;utf-8"
    });

    if (response == null) {
      var requestError = module.getApiRequestLastError();
      if (module.settings.log) {
        h.log(CATEDRAL_VIDEO_PREVIEW_MODULE_ID,
          "Falha ao enviar URL ao Controle Catedral: " +
          String(requestError || "A requisição retornou null.") +
          " | endpoint: " + endpoint);
      }
      return false;
    }

    if (module.settings.log) {
      h.log(CATEDRAL_VIDEO_PREVIEW_MODULE_ID,
        "URL do vídeo enviada ao Controle Catedral: " + payload.name +
        " | resposta: " + String(response).substring(0, 180));
    }
    return true;
  } catch (e) {
    if (module.settings.log) {
      h.log(CATEDRAL_VIDEO_PREVIEW_MODULE_ID,
        "Falha ao enviar URL ao Controle Catedral (" + endpoint + "): " + String(e));
    }
    return false;
  }
}

function publicarUrlVideoCatedral(module, obj) {
  var fullPath = String(obj && obj.file_fullname || "").trim();
  if (!fullPath) {
    if (module.settings.log) h.log(CATEDRAL_VIDEO_PREVIEW_MODULE_ID, "O Holyrics não informou o caminho do vídeo.");
    return;
  }

  var pluginSettings = readPluginVideoSettings();
  if (!pluginSettings) {
    if (module.settings.log) h.log(CATEDRAL_VIDEO_PREVIEW_MODULE_ID,
      "Não foi possível ler .plugin_system_settings.txt do serviço de vídeo do Holyrics.");
    return;
  }

  try {
    var url = createCatedralVideoUrl(pluginSettings, fullPath);
    var normalized = fullPath.replace(/\\/g, "/");
    var fileName = normalized.substring(normalized.lastIndexOf("/") + 1);

    enviarUrlAoAplicativo(module, {
      available: true,
      url: url,
      path: fullPath,
      name: fileName,
      updated_at: new Date().getTime()
    });
  } catch (e) {
    if (module.settings.log) h.log(CATEDRAL_VIDEO_PREVIEW_MODULE_ID,
      "Falha ao gerar a URL do vídeo: " + String(e));
  }
}

function triggers(module) {
  return [{
    id: "enviar_url_video_catedral",
    when: "displaying",
    item: "any_video",
    action: function (obj) {
      publicarUrlVideoCatedral(module, obj);
    }
  }];
}
