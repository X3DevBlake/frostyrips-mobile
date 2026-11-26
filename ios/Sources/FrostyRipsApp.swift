import SwiftUI

@main
struct FrostyRipsApp: App {
    @StateObject private var router = FrostyAppRouter()

    var body: some Scene {
        WindowGroup {
            FrostyRootView()
                .environmentObject(router)
                .preferredColorScheme(.dark)
                .onOpenURL { url in
                    router.handleDeepLink(url)
                }
        }
    }
}

final class FrostyAppRouter: ObservableObject {
    static let packsURL = URL(string: "https://frostrips.web.app/?app=ios&v=1.0.0")!
    static let stadiumURL = URL(string: "https://frostyrips-stadium.web.app/?app=ios&v=1.0.0")!
    static let presaleURL = URL(string: "https://frostyrips-presale.web.app/?app=ios&v=1.0.0")!

    @Published var currentURL: URL = FrostyAppRouter.packsURL
    @Published var isLoading: Bool = true
    @Published var loadFailed: Bool = false

    func handleDeepLink(_ url: URL) {
        if url.scheme?.lowercased() == "frostyrips" {
            if url.host?.lowercased() == "stadium" {
                currentURL = Self.stadiumURL
                return
            }
            if url.host?.lowercased() == "presale" {
                currentURL = Self.presaleURL
                return
            }
            let path = url.path.isEmpty ? "/" : url.path
            var comps = URLComponents(string: "https://frostrips.web.app\(path)")
            var items = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems ?? []
            items.append(URLQueryItem(name: "app", value: "ios"))
            comps?.queryItems = items
            if let resolved = comps?.url {
                currentURL = resolved
            }
            return
        }
        if let host = url.host?.lowercased(),
           host == "frostrips.web.app"
            || host == "frostyrips-stadium.web.app"
            || host == "frostyrips-presale.web.app" {
            currentURL = url
        }
    }
}

struct FrostyRootView: View {
    @EnvironmentObject private var router: FrostyAppRouter
    @State private var reloadToken = UUID()

    var body: some View {
        ZStack {
            Color(red: 5/255, green: 10/255, blue: 22/255)
                .ignoresSafeArea()

            FrostyWebView(
                url: router.currentURL,
                reloadToken: reloadToken,
                isLoading: $router.isLoading,
                loadFailed: $router.loadFailed
            )
            .ignoresSafeArea(edges: .bottom)

            if router.isLoading {
                FrostySplashView()
                    .transition(.opacity.animation(.easeOut(duration: 0.3)))
            }

            if router.loadFailed {
                VStack(spacing: 16) {
                    Text("ICE STORM CONNECTION LOST")
                        .font(.system(size: 20, weight: .heavy, design: .rounded))
                        .foregroundColor(Color(red: 0/255, green: 229/255, blue: 255/255))
                    Text("Connect to Wi-Fi or cellular data to rip FrostyRips foil packs and enter the 3D Stadium.")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(Color.white.opacity(0.72))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 28)
                    Button {
                        router.loadFailed = false
                        router.isLoading = true
                        reloadToken = UUID()
                    } label: {
                        Text("RETRY CONNECTION")
                            .font(.system(size: 15, weight: .black))
                            .foregroundColor(Color(red: 4/255, green: 21/255, blue: 33/255))
                            .padding(.horizontal, 28)
                            .padding(.vertical, 14)
                            .background(
                                LinearGradient(
                                    colors: [Color(red: 0/255, green: 255/255, blue: 247/255), Color(red: 44/255, green: 160/255, blue: 255/255)],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Color(red: 5/255, green: 10/255, blue: 22/255).ignoresSafeArea())
            }
        }
    }
}

struct FrostySplashView: View {
    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    Color(red: 10/255, green: 26/255, blue: 54/255),
                    Color(red: 5/255, green: 10/255, blue: 22/255),
                    Color(red: 3/255, green: 6/255, blue: 14/255)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            VStack(spacing: 14) {
                Image("SplashIcon")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 112, height: 112)
                    .clipShape(RoundedRectangle(cornerRadius: 26, style: .continuous))
                    .shadow(color: Color(red: 0/255, green: 229/255, blue: 255/255).opacity(0.45), radius: 22)

                Text("FROSTYRIPS")
                    .font(.system(size: 32, weight: .black, design: .rounded))
                    .tracking(4)
                    .foregroundColor(Color(red: 255/255, green: 229/255, blue: 0/255))

                Text("FOIL PACKS  •  FREE VAULT  •  3D STADIUM")
                    .font(.system(size: 11, weight: .bold))
                    .tracking(2)
                    .foregroundColor(Color(red: 125/255, green: 211/255, blue: 252/255))

                ProgressView()
                    .tint(Color(red: 0/255, green: 229/255, blue: 255/255))
                    .padding(.top, 12)
            }
        }
    }
}
