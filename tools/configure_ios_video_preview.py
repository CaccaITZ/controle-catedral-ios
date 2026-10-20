#!/usr/bin/env python3
"""Inject the native iOS HTTP receiver and register it in the generated Capacitor ViewController."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VIEW_CONTROLLER = ROOT / "ios" / "App" / "App" / "ViewController.swift"

SWIFT_PLUGIN = r'''

@objc(VideoPreviewServerPlugin)
public class VideoPreviewServerPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "VideoPreviewServerPlugin"
    public let jsName = "VideoPreviewServer"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "start", returnType: CAPPluginReturnPromise)
    ]

    private let listenerQueue = DispatchQueue(label: "br.com.catedral.video-preview-server")
    private var listener: NWListener?
    private var isReady = false
    private var lastPayload: [String: Any]?
    private let defaultPort: UInt16 = 8766
    private let maxBodyBytes = 65536
    private let maxHeaderBytes = 16384

    @objc func start(_ call: CAPPluginCall) {
        let requestedInt = call.getInt("port") ?? Int(defaultPort)
        guard requestedInt >= 1024 && requestedInt <= 65535,
              let port = NWEndpoint.Port(rawValue: UInt16(requestedInt)) else {
            call.reject("A porta do receptor deve estar entre 1024 e 65535.")
            return
        }

        if isReady && listener != nil {
            var result: [String: Any] = ["started": true, "port": requestedInt]
            if let payload = lastPayload { result["lastPayload"] = payload }
            call.resolve(result)
            return
        }

        do {
            let newListener = try NWListener(using: .tcp, on: port)
            listener = newListener
            isReady = false
            newListener.stateUpdateHandler = { [weak self] state in
                guard let self = self else { return }
                switch state {
                case .ready:
                    self.isReady = true
                    var result: [String: Any] = ["started": true, "port": requestedInt]
                    if let payload = self.lastPayload { result["lastPayload"] = payload }
                    DispatchQueue.main.async { call.resolve(result) }
                case .failed(let error):
                    self.isReady = false
                    self.listener = nil
                    DispatchQueue.main.async {
                        call.reject("Não foi possível iniciar o receptor HTTP na porta \(requestedInt): \(error.localizedDescription)")
                    }
                default:
                    break
                }
            }
            newListener.newConnectionHandler = { [weak self] connection in
                guard let self = self else { return }
                connection.start(queue: self.listenerQueue)
                self.receiveMore(connection, accumulated: Data())
            }
            newListener.start(queue: listenerQueue)
        } catch {
            listener = nil
            isReady = false
            call.reject("Não foi possível iniciar o receptor HTTP: \(error.localizedDescription)")
        }
    }

    private func receiveMore(_ connection: NWConnection, accumulated: Data) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] data, _, isComplete, error in
            guard let self = self else {
                connection.cancel()
                return
            }

            var combined = accumulated
            if let data = data { combined.append(data) }

            if self.requestIsComplete(combined) {
                self.processRequest(combined, connection: connection)
            } else if isComplete || error != nil {
                self.sendResponse(connection, status: 400, reason: "Bad Request",
                                  body: self.errorJSON("Requisição HTTP incompleta."))
            } else {
                self.receiveMore(connection, accumulated: combined)
            }
        }
    }

    private func requestIsComplete(_ data: Data) -> Bool {
        let delimiter = Data([13, 10, 13, 10])
        guard let range = data.range(of: delimiter) else {
            return data.count > maxHeaderBytes
        }
        let headerData = data.subdata(in: 0..<range.lowerBound)
        let headerText = String(data: headerData, encoding: .utf8) ?? ""
        var contentLength = 0
        for line in headerText.components(separatedBy: "\r\n") {
            let parts = line.split(separator: ":", maxSplits: 1)
            if parts.count == 2 && parts[0].trimmingCharacters(in: .whitespaces).lowercased() == "content-length" {
                contentLength = Int(parts[1].trimmingCharacters(in: .whitespaces)) ?? 0
            }
        }
        if contentLength < 0 || contentLength > maxBodyBytes { return true }
        return data.count >= range.upperBound + contentLength
    }

    private func processRequest(_ data: Data, connection: NWConnection) {
        let delimiter = Data([13, 10, 13, 10])
        guard let range = data.range(of: delimiter) else {
            sendResponse(connection, status: 400, reason: "Bad Request",
                         body: errorJSON("Cabeçalho HTTP inválido."))
            return
        }

        let headerData = data.subdata(in: 0..<range.lowerBound)
        let headerText = String(data: headerData, encoding: .utf8) ?? ""
        let lines = headerText.components(separatedBy: "\r\n")
        guard let requestLine = lines.first else {
            sendResponse(connection, status: 400, reason: "Bad Request",
                         body: errorJSON("Linha de requisição ausente."))
            return
        }
        let parts = requestLine.split(separator: " ", maxSplits: 2).map(String.init)
        guard parts.count >= 2 else {
            sendResponse(connection, status: 400, reason: "Bad Request",
                         body: errorJSON("Linha HTTP inválida."))
            return
        }

        let method = parts[0].uppercased()
        let path = parts[1].components(separatedBy: "?").first ?? parts[1]
        var contentLength = 0
        for line in lines.dropFirst() {
            let parts = line.split(separator: ":", maxSplits: 1)
            if parts.count == 2 && parts[0].trimmingCharacters(in: .whitespaces).lowercased() == "content-length" {
                contentLength = Int(parts[1].trimmingCharacters(in: .whitespaces)) ?? 0
            }
        }

        if contentLength > maxBodyBytes {
            sendResponse(connection, status: 413, reason: "Payload Too Large",
                         body: errorJSON("Corpo da requisição muito grande."))
            return
        }
        if method == "OPTIONS" {
            sendResponse(connection, status: 204, reason: "No Content", body: "")
            return
        }
        if method == "GET" && path == "/health" {
            sendResponse(connection, status: 200, reason: "OK",
                         body: "{\"status\":\"ok\",\"port\":\(listener?.port?.rawValue ?? defaultPort)}")
            return
        }
        guard method == "POST" && path == "/api/video-preview" else {
            sendResponse(connection, status: 404, reason: "Not Found",
                         body: errorJSON("Endpoint não encontrado."))
            return
        }

        let bodyStart = range.upperBound
        let bodyEnd = bodyStart + contentLength
        guard data.count >= bodyEnd else {
            sendResponse(connection, status: 400, reason: "Bad Request",
                         body: errorJSON("Corpo HTTP incompleto."))
            return
        }
        let bodyData = data.subdata(in: bodyStart..<bodyEnd)
        guard let payload = (try? JSONSerialization.jsonObject(with: bodyData)) as? [String: Any],
              let urlString = payload["url"] as? String,
              let components = URLComponents(string: urlString),
              (components.scheme == "http" || components.scheme == "https"),
              components.path.lowercased() == "/get_video" else {
            sendResponse(connection, status: 400, reason: "Bad Request",
                         body: errorJSON("O corpo precisa conter uma URL HTTP(S) válida de /get_video."))
            return
        }

        lastPayload = payload
        let eventData = JSObject()
        for (key, value) in payload {
            eventData[key] = value
        }
        DispatchQueue.main.async {
            self.notifyListeners("videoPreviewReceived", data: eventData)
        }
        sendResponse(connection, status: 200, reason: "OK",
                     body: "{\"status\":\"ok\",\"received\":true}")
    }

    private func errorJSON(_ message: String) -> String {
        let safe = message.replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
        return "{\"status\":\"error\",\"error\":\"\(safe)\"}"
    }

    private func sendResponse(_ connection: NWConnection, status: Int, reason: String, body: String) {
        let bodyData = Data(body.utf8)
        let header = "HTTP/1.1 \(status) \(reason)\r\n" +
            "Content-Type: application/json; charset=utf-8\r\n" +
            "Content-Length: \(bodyData.count)\r\n" +
            "Cache-Control: no-store\r\n" +
            "Connection: close\r\n" +
            "Access-Control-Allow-Origin: *\r\n" +
            "Access-Control-Allow-Methods: POST, OPTIONS\r\n" +
            "Access-Control-Allow-Headers: Content-Type\r\n\r\n"
        var response = Data(header.utf8)
        response.append(bodyData)
        connection.send(content: response, completion: .contentProcessed { _ in connection.cancel() })
    }
}
'''

if not VIEW_CONTROLLER.exists():
    raise SystemExit("ViewController.swift não encontrado em: " + str(VIEW_CONTROLLER))

source = VIEW_CONTROLLER.read_text(encoding="utf-8")
if "import Network" not in source:
    source = source.replace("import Capacitor", "import Capacitor\nimport Network", 1)

if "VideoPreviewServerPlugin" not in source:
    empty_class = re.search(r"class ViewController\s*:\s*CAPBridgeViewController\s*\{\s*\}", source)
    if empty_class:
        replacement = (
            "class ViewController: CAPBridgeViewController {\n"
            "    override func capacitorDidLoad() {\n"
            "        bridge?.registerPluginInstance(VideoPreviewServerPlugin())\n"
            "    }\n"
            "}"
        )
        source = source[:empty_class.start()] + replacement + source[empty_class.end():]
    elif "registerPluginInstance(VideoPreviewServerPlugin())" not in source:
        raise SystemExit("Não foi possível localizar ViewController para registrar o receptor.")

    source += "\n" + SWIFT_PLUGIN + "\n"

VIEW_CONTROLLER.write_text(source, encoding="utf-8")
print("VideoPreviewServerPlugin registrado em ViewController.swift.")
