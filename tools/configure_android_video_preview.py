#!/usr/bin/env python3
"""Inject the native Android HTTP receiver used by the Holyrics video-preview push module.

The CI workflow creates the Capacitor Android project from scratch, so this script
registers the native plugin and writes its Java implementation after "cap add android".
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
JAVA_DIR = ROOT / "android" / "app" / "src" / "main" / "java" / "br" / "com" / "catedral"
JAVA_DIR.mkdir(parents=True, exist_ok=True)

JAVA_SOURCE = r'''package br.com.catedral;

import android.util.Log;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.NetworkInterface;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.util.Enumeration;
import java.util.Iterator;

@CapacitorPlugin(name = "VideoPreviewServer")
public class VideoPreviewServerPlugin extends Plugin {
    private static final String TAG = "VideoPreviewServer";
    private static final int DEFAULT_PORT = 8766;
    private static final int MAX_BODY_BYTES = 65536;

    private volatile boolean running = false;
    private volatile int listeningPort = DEFAULT_PORT;
    private volatile ServerSocket serverSocket;
    private volatile String lastPayloadJson = null;

    @PluginMethod
    public void start(PluginCall call) {
        int requestedPort = call.getInt("port", DEFAULT_PORT);
        if (requestedPort < 1024 || requestedPort > 65535) {
            call.reject("A porta do receptor deve estar entre 1024 e 65535.");
            return;
        }

        try {
            startServer(requestedPort);
            JSObject result = new JSObject();
            result.put("started", true);
            result.put("port", listeningPort);
            result.put("addresses", getLocalIPv4Addresses());
            if (lastPayloadJson != null) {
                try {
                    result.put("lastPayload", new JSONObject(lastPayloadJson));
                } catch (JSONException ignored) {
                }
            }
            call.resolve(result);
        } catch (IOException e) {
            Log.e(TAG, "Não foi possível iniciar o receptor HTTP", e);
            call.reject("Não foi possível iniciar o receptor HTTP na porta " + requestedPort + ": " + e.getMessage());
        }
    }

    private synchronized void startServer(int port) throws IOException {
        if (running && serverSocket != null && !serverSocket.isClosed() && listeningPort == port) {
            return;
        }
        stopServer();

        ServerSocket socket = new ServerSocket();
        socket.setReuseAddress(true);
        socket.bind(new InetSocketAddress(InetAddress.getByName("0.0.0.0"), port), 24);
        socket.setSoTimeout(0);

        serverSocket = socket;
        listeningPort = port;
        running = true;

        Thread thread = new Thread(() -> acceptLoop(socket), "CatedralVideoPreviewAccept");
        thread.setDaemon(true);
        thread.start();
    }

    private void acceptLoop(ServerSocket socket) {
        while (running && socket == serverSocket && !socket.isClosed()) {
            try {
                Socket client = socket.accept();
                Thread worker = new Thread(() -> handleClient(client), "CatedralVideoPreviewClient");
                worker.setDaemon(true);
                worker.start();
            } catch (SocketTimeoutException ignored) {
            } catch (IOException e) {
                if (running) Log.w(TAG, "Falha ao aceitar conexão HTTP", e);
                break;
            }
        }
    }

    private void handleClient(Socket client) {
        try (Socket socket = client) {
            socket.setSoTimeout(6000);
            InputStream input = socket.getInputStream();
            OutputStream output = socket.getOutputStream();

            ByteArrayOutputStream headerBytes = new ByteArrayOutputStream();
            int matched = 0;
            while (headerBytes.size() < 16384) {
                int value = input.read();
                if (value < 0) throw new IOException("Cabeçalho HTTP incompleto");
                headerBytes.write(value);
                if ((matched == 0 && value == 13) ||
                    (matched == 1 && value == 10) ||
                    (matched == 2 && value == 13) ||
                    (matched == 3 && value == 10)) {
                    matched++;
                } else {
                    matched = value == 13 ? 1 : 0;
                }
                if (matched == 4) break;
            }

            String headersText = new String(headerBytes.toByteArray(), StandardCharsets.US_ASCII);
            String[] lines = headersText.split("\\r\\n");
            if (lines.length == 0) {
                writeResponse(output, 400, "Bad Request", errorJson("Cabeçalho HTTP vazio."));
                return;
            }

            String[] first = lines[0].split(" ", 3);
            if (first.length < 2) {
                writeResponse(output, 400, "Bad Request", errorJson("Linha HTTP inválida."));
                return;
            }

            String method = first[0].toUpperCase();
            String path = first[1].split("\\?", 2)[0];
            int contentLength = 0;
            for (int i = 1; i < lines.length; i++) {
                int colon = lines[i].indexOf(':');
                if (colon <= 0) continue;
                String key = lines[i].substring(0, colon).trim().toLowerCase();
                String value = lines[i].substring(colon + 1).trim();
                if ("content-length".equals(key)) {
                    try { contentLength = Integer.parseInt(value); } catch (NumberFormatException ignored) { }
                }
            }

            if (contentLength < 0 || contentLength > MAX_BODY_BYTES) {
                writeResponse(output, 413, "Payload Too Large", errorJson("Corpo da requisição muito grande."));
                return;
            }

            if ("OPTIONS".equals(method)) {
                writeResponse(output, 204, "No Content", "");
                return;
            }

            if (!"POST".equals(method) || !"/api/video-preview".equals(path)) {
                if ("GET".equals(method) && "/health".equals(path)) {
                    JSONObject health = new JSONObject();
                    health.put("status", "ok");
                    health.put("port", listeningPort);
                    writeResponse(output, 200, "OK", health.toString());
                } else {
                    writeResponse(output, 404, "Not Found", errorJson("Endpoint não encontrado."));
                }
                return;
            }

            byte[] bodyBytes = readExact(input, contentLength);
            if (bodyBytes.length != contentLength) {
                writeResponse(output, 400, "Bad Request", errorJson("Corpo HTTP incompleto."));
                return;
            }

            String body = new String(bodyBytes, StandardCharsets.UTF_8);
            JSONObject payload;
            try {
                payload = new JSONObject(body);
            } catch (JSONException e) {
                writeResponse(output, 400, "Bad Request", errorJson("JSON inválido."));
                return;
            }

            String videoUrl = payload.optString("url", "").trim();
            if (!(videoUrl.startsWith("http://") || videoUrl.startsWith("https://")) ||
                !videoUrl.matches("(?i)^https?://[^/]+/get_video(?:\\?.*)?$")) {
                writeResponse(output, 400, "Bad Request", errorJson("Informe uma URL HTTP(S) válida de /get_video."));
                return;
            }

            lastPayloadJson = payload.toString();
            JSObject eventData = new JSObject();
            Iterator<String> keys = payload.keys();
            while (keys.hasNext()) {
                String key = keys.next();
                eventData.put(key, payload.opt(key));
            }
            notifyListeners("videoPreviewReceived", eventData);

            JSONObject response = new JSONObject();
            response.put("status", "ok");
            response.put("received", true);
            writeResponse(output, 200, "OK", response.toString());
        } catch (Exception e) {
            Log.w(TAG, "Erro processando requisição da prévia", e);
            try {
                OutputStream output = client.getOutputStream();
                writeResponse(output, 400, "Bad Request", errorJson("Não foi possível processar a requisição."));
            } catch (Exception ignored) {
            }
        }
    }

    private byte[] readExact(InputStream input, int count) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[Math.min(4096, Math.max(1, count))];
        int total = 0;
        while (total < count) {
            int read = input.read(buffer, 0, Math.min(buffer.length, count - total));
            if (read < 0) break;
            output.write(buffer, 0, read);
            total += read;
        }
        return output.toByteArray();
    }

    private void writeResponse(OutputStream output, int status, String reason, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        String header = "HTTP/1.1 " + status + " " + reason + "\r\n" +
            "Content-Type: application/json; charset=utf-8\r\n" +
            "Content-Length: " + bytes.length + "\r\n" +
            "Cache-Control: no-store\r\n" +
            "Connection: close\r\n" +
            "Access-Control-Allow-Origin: *\r\n" +
            "Access-Control-Allow-Methods: POST, OPTIONS\r\n" +
            "Access-Control-Allow-Headers: Content-Type\r\n\r\n";
        output.write(header.getBytes(StandardCharsets.US_ASCII));
        output.write(bytes);
        output.flush();
    }

    private String errorJson(String message) {
        JSONObject json = new JSONObject();
        try {
            json.put("status", "error");
            json.put("error", message);
        } catch (JSONException ignored) {
        }
        return json.toString();
    }

    private JSONArray getLocalIPv4Addresses() {
        JSONArray addresses = new JSONArray();
        try {
            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            while (interfaces != null && interfaces.hasMoreElements()) {
                NetworkInterface network = interfaces.nextElement();
                if (!network.isUp() || network.isLoopback()) continue;
                Enumeration<InetAddress> inetAddresses = network.getInetAddresses();
                while (inetAddresses.hasMoreElements()) {
                    InetAddress address = inetAddresses.nextElement();
                    if (address instanceof Inet4Address && !address.isLoopbackAddress()) {
                        addresses.put(address.getHostAddress());
                    }
                }
            }
        } catch (Exception e) {
            Log.w(TAG, "Não foi possível obter os IPs locais", e);
        }
        return addresses;
    }
}
'''

java_path = JAVA_DIR / "VideoPreviewServerPlugin.java"
java_path.write_text(JAVA_SOURCE, encoding="utf-8")

activity_path = ROOT / "android" / "app" / "src" / "main" / "java" / "br" / "com" / "catedral" / "MainActivity.java"
if not activity_path.exists():
    raise SystemExit("MainActivity.java não encontrado no caminho esperado: " + str(activity_path))

activity = activity_path.read_text(encoding="utf-8")
if "VideoPreviewServerPlugin.class" not in activity:
    if "import com.getcapacitor.BridgeActivity;" not in activity:
        raise SystemExit("Importação BridgeActivity não encontrada em MainActivity.java")
    activity = activity.replace(
        "import com.getcapacitor.BridgeActivity;",
        "import com.getcapacitor.BridgeActivity;\nimport android.os.Bundle;"
    )
    activity = re.sub(
        r"public class MainActivity extends BridgeActivity\s*\{\s*\}",
        "public class MainActivity extends BridgeActivity {\n"
        "    @Override\n"
        "    public void onCreate(Bundle savedInstanceState) {\n"
        "        registerPlugin(VideoPreviewServerPlugin.class);\n"
        "        super.onCreate(savedInstanceState);\n"
        "    }\n"
        "}",
        activity
    )
    if "VideoPreviewServerPlugin.class" not in activity:
        raise SystemExit("Não foi possível registrar VideoPreviewServerPlugin em MainActivity.java")
    activity_path.write_text(activity, encoding="utf-8")

print("VideoPreviewServerPlugin.java criado e registrado em MainActivity.java.")
