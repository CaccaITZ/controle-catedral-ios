/*
 * Prévia de Vídeo — Catedral (envio direto ao aplicativo)
 * Holyrics 2.24+
 *
 * Ao exibir um vídeo, calcula a mesma URL autenticada usada pelo módulo
 * Video Sync OBS+ e faz POST diretamente ao receptor do Controle Catedral.
 * Não consulta nem controla o OBS.
 *
 * Para o teste no PC, configure o IP 127.0.0.1 e a porta 8766.
 * No aparelho, configure o IP local do celular/tablet e a porta 8766.
 */

var CATEDRAL_VIDEO_PREVIEW_MODULE_ID = "catedral_video_preview_push";

function info() {
  return {
    id: CATEDRAL_VIDEO_PREVIEW_MODULE_ID,
    name: "Prévia de Vídeo — Envio ao Controle Catedral",
    description: "Envia diretamente ao Controle Catedral a URL autenticada do vídeo exibido no Holyrics. Não depende do OBS.",
    min_version: "2.24.0",
    available_in_main_window: true,
    available_in_bible_window: false
  };
}

function settings() {
  return [
    {
      type: "label",
      name: "Envie a URL do vídeo diretamente ao aplicativo. Não é necessário usar o OBS para esta função."
    },
    {
      id: "app_ip",
      name: "IP do dispositivo Controle Catedral",
      type: "string",
      default_value: "127.0.0.1"
    },
    {
      id: "app_port",
      name: "Porta receptora HTTP",
      type: "number",
      min: 1024,
      max: 65535,
      default_value: 8766
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
  var receiverIp = String(module.settings.app_ip || "").trim();
  var receiverPort = Number(module.settings.app_port || 8766);

  if (!receiverIp || /[\s/?#]/.test(receiverIp) ||
      !isFinite(receiverPort) || receiverPort < 1024 || receiverPort > 65535) {
    if (module.settings.log) h.log(CATEDRAL_VIDEO_PREVIEW_MODULE_ID, "Configure o IP e a porta do Controle Catedral.");
    return false;
  }

  var endpoint = "http://" + receiverIp + ":" + receiverPort + "/api/video-preview";

  try {
    var response = h.httpRequest(endpoint, {
      type: "POST",
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify(payload),
      timeout: 3000,
      response_data_type: "string;utf-8"
    });

    if (module.settings.log) {
      h.log(CATEDRAL_VIDEO_PREVIEW_MODULE_ID,
        "URL do vídeo enviada ao Controle Catedral: " + payload.name +
        " | resposta: " + String(response == null ? "" : response).substring(0, 180));
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
