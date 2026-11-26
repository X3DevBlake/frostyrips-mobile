import SwiftUI
import UIKit
import WebKit

struct FrostyWebView: UIViewRepresentable {
    let url: URL
    let reloadToken: UUID
    @Binding var isLoading: Bool
    @Binding var loadFailed: Bool

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []
        config.websiteDataStore = .default()
        config.applicationNameForUserAgent = "FrostyRipsApp/1.0.0 iOSNative"

        let controller = WKUserContentController()
        controller.add(context.coordinator, name: "frostyNative")

        // Unified FrostyNative bridge matching Android's window.FrostyNative API
        let bridgeJS = """
        window.FrostyNative = {
          vibrate: function(ms) {
            window.webkit.messageHandlers.frostyNative.postMessage({ action: 'vibrate', ms: ms || 25 });
          },
          share: function(title, text, url) {
            window.webkit.messageHandlers.frostyNative.postMessage({ action: 'share', title: title || 'FrostyRips', text: text || '', url: url || location.href });
          },
          copyText: function(text) {
            window.webkit.messageHandlers.frostyNative.postMessage({ action: 'copyText', text: text || '' });
          },
          openStadium: function() {
            window.webkit.messageHandlers.frostyNative.postMessage({ action: 'openStadium' });
          },
          openPacks: function() {
            window.webkit.messageHandlers.frostyNative.postMessage({ action: 'openPacks' });
          },
          openPresale: function() {
            window.webkit.messageHandlers.frostyNative.postMessage({ action: 'openPresale' });
          },
          getAppInfo: function() {
            return JSON.stringify({ platform: 'ios', version: '1.0.0', bundle: 'com.frostyrips.app' });
          }
        };
        """
        controller.addUserScript(WKUserScript(source: bridgeJS, injectionTime: .atDocumentStart, forMainFrameOnly: false))
        config.userContentController = controller

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        webView.isOpaque = false
        webView.backgroundColor = UIColor(red: 5/255, green: 10/255, blue: 22/255, alpha: 1)
        webView.scrollView.backgroundColor = UIColor(red: 5/255, green: 10/255, blue: 22/255, alpha: 1)
        webView.scrollView.contentInsetAdjustmentBehavior = .automatic

        context.coordinator.webView = webView
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {
        if context.coordinator.lastURL != url || context.coordinator.lastReloadToken != reloadToken {
            context.coordinator.lastURL = url
            context.coordinator.lastReloadToken = reloadToken
            uiView.load(URLRequest(url: url))
        }
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
        var parent: FrostyWebView
        weak var webView: WKWebView?
        var lastURL: URL?
        var lastReloadToken: UUID?

        init(_ parent: FrostyWebView) {
            self.parent = parent
            self.lastURL = parent.url
            self.lastReloadToken = parent.reloadToken
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            DispatchQueue.main.async {
                self.parent.isLoading = false
                self.parent.loadFailed = false
            }
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            let nsErr = error as NSError
            if nsErr.code == NSURLErrorCancelled { return }
            DispatchQueue.main.async {
                self.parent.isLoading = false
                self.parent.loadFailed = true
            }
        }

        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard let target = navigationAction.request.url else {
                decisionHandler(.allow)
                return
            }
            let scheme = (target.scheme ?? "").lowercased()
            let host = (target.host ?? "").lowercased()

            if scheme == "frostyrips" {
                if host == "stadium" {
                    webView.load(URLRequest(url: FrostyAppRouter.stadiumURL))
                } else if host == "presale" {
                    webView.load(URLRequest(url: FrostyAppRouter.presaleURL))
                } else {
                    webView.load(URLRequest(url: FrostyAppRouter.packsURL))
                }
                decisionHandler(.cancel)
                return
            }

            if (scheme == "https" || scheme == "http") &&
                (host.hasSuffix("frostrips.web.app")
                 || host.hasSuffix("frostyrips-stadium.web.app")
                 || host.hasSuffix("frostyrips-presale.web.app")
                 || host.hasSuffix("firebaseapp.com")) {
                decisionHandler(.allow)
                return
            }

            if navigationAction.navigationType == .linkActivated {
                UIApplication.shared.open(target)
                decisionHandler(.cancel)
                return
            }
            decisionHandler(.allow)
        }

        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            guard let dict = message.body as? [String: Any],
                  let action = dict["action"] as? String else { return }

            switch action {
            case "vibrate":
                let ms = dict["ms"] as? Int ?? 25
                let style: UIImpactFeedbackGenerator.FeedbackStyle = ms > 55 ? .heavy : (ms > 28 ? .medium : .light)
                let gen = UIImpactFeedbackGenerator(style: style)
                gen.prepare()
                gen.impactOccurred()
            case "copyText":
                if let txt = dict["text"] as? String {
                    UIPasteboard.general.string = txt
                }
            case "openStadium":
                webView?.load(URLRequest(url: FrostyAppRouter.stadiumURL))
            case "openPacks":
                webView?.load(URLRequest(url: FrostyAppRouter.packsURL))
            case "openPresale":
                webView?.load(URLRequest(url: FrostyAppRouter.presaleURL))
            case "share":
                let text = dict["text"] as? String ?? "Claim a free FrostyRips Foil Pack!"
                let urlStr = dict["url"] as? String ?? "https://frostrips.web.app/ad/landing/app"
                var items: [Any] = [text]
                if let shareURL = URL(string: urlStr) { items.append(shareURL) }
                DispatchQueue.main.async {
                    guard let scene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
                          let rootVC = scene.windows.first?.rootViewController else { return }
                    let vc = UIActivityViewController(activityItems: items, applicationActivities: nil)
                    if let pop = vc.popoverPresentationController {
                        pop.sourceView = rootVC.view
                        pop.sourceRect = CGRect(x: rootVC.view.bounds.midX, y: rootVC.view.bounds.midY, width: 0, height: 0)
                        pop.permittedArrowDirections = []
                    }
                    rootVC.present(vc, animated: true)
                }
            default:
                break
            }
        }
    }
}
