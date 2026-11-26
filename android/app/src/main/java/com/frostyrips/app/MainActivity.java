package com.frostyrips.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.ClipDrawable;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.Message;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private static final String APP_VERSION = "1.1.0";
    private static final String PACKS_URL = "https://frostrips.web.app/?app=android&v=" + APP_VERSION;
    private static final String STADIUM_URL = "https://frostyrips-stadium.web.app/?app=android&v=" + APP_VERSION;
    private static final String PRESALE_URL = "https://frostyrips-presale.web.app/?app=android&v=" + APP_VERSION;
    private static final int FILE_CHOOSER_REQ = 4091;

    private FrameLayout root;
    private WebView webView;
    private LinearLayout splashOverlay;
    private LinearLayout offlineOverlay;
    private ProgressBar topProgress;
    private TextView returnToPacksPill;
    private boolean splashDismissed = false;
    private long lastBackPressMs = 0L;
    private String lastLoadedUrl = PACKS_URL;
    private ValueCallback<Uri[]> filePathCallback;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Window win = getWindow();
        win.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        win.setStatusBarColor(Color.parseColor("#050A16"));
        win.setNavigationBarColor(Color.parseColor("#050A16"));
        win.getDecorView().setBackgroundColor(Color.parseColor("#050A16"));

        root = new FrameLayout(this);
        root.setLayoutParams(new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));
        root.setBackgroundColor(Color.parseColor("#050A16"));
        root.setFitsSystemWindows(true);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            root.setOnApplyWindowInsetsListener((v, insets) -> {
                android.graphics.Insets sys = insets.getInsets(
                        WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout() | WindowInsets.Type.ime());
                v.setPadding(sys.left, sys.top, sys.right, sys.bottom);
                return WindowInsets.CONSUMED;
            });
        }

        // 1. Hardware-Accelerated WebView (default LAYER_TYPE_NONE so Chromium's native GPU compositor runs glitch-free)
        webView = createConfiguredWebView();
        root.addView(webView);

        // 2. Slim Neon Cyan Top Progress Bar
        topProgress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        FrameLayout.LayoutParams progLp = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(3));
        progLp.gravity = Gravity.TOP;
        topProgress.setLayoutParams(progLp);
        topProgress.setMax(100);
        topProgress.setProgressDrawable(createProgressDrawable());
        root.addView(topProgress);

        // 3. Sleek Floating Quick-Return Pill (shown only when inside fullscreen Stadium or Presale)
        returnToPacksPill = buildReturnPill();
        returnToPacksPill.setVisibility(View.GONE);
        root.addView(returnToPacksPill);

        // 4. Branded FrostyRips Offline Recovery Overlay
        offlineOverlay = buildOfflineView();
        offlineOverlay.setVisibility(View.GONE);
        root.addView(offlineOverlay);

        // 5. Native FrostyRips Splash Screen Overlay
        splashOverlay = buildSplashView();
        root.addView(splashOverlay);

        setContentView(root);

        // Failsafe dismiss splash after 3.2s even on slow cellular networks
        mainHandler.postDelayed(this::dismissSplash, 3200);

        String targetUrl = resolveInitialUrl(getIntent());
        lastLoadedUrl = targetUrl;
        if (isNetworkAvailable()) {
            webView.loadUrl(targetUrl);
        } else {
            dismissSplash();
            offlineOverlay.setVisibility(View.VISIBLE);
        }
    }

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    private WebView createConfiguredWebView() {
        WebView wv = new WebView(this);
        wv.setLayoutParams(new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));
        wv.setBackgroundColor(Color.parseColor("#050A16"));
        // IMPORTANT: Do NOT call setLayerType(LAYER_TYPE_HARDWARE, null) on WebView —
        // Chromium already hardware-accelerates via AndroidManifest; forcing HWUI layer causes WebGL flicker/tearing.
        wv.setOverScrollMode(View.OVER_SCROLL_NEVER);
        wv.setHorizontalScrollBarEnabled(false);

        WebSettings ws = wv.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setDatabaseEnabled(true);
        ws.setMediaPlaybackRequiresUserGesture(false);
        ws.setUseWideViewPort(true);
        ws.setLoadWithOverviewMode(true);
        ws.setTextZoom(100);
        ws.setAllowFileAccess(false);
        ws.setAllowContentAccess(true);
        ws.setSupportZoom(false);
        ws.setBuiltInZoomControls(false);
        ws.setDisplayZoomControls(false);
        ws.setSupportMultipleWindows(true);
        ws.setJavaScriptCanOpenWindowsAutomatically(true);
        ws.setCacheMode(WebSettings.LOAD_DEFAULT);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            ws.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        }
        String ua = ws.getUserAgentString();
        ws.setUserAgentString(ua + " FrostyRipsApp/" + APP_VERSION + " AndroidNative");

        CookieManager cm = CookieManager.getInstance();
        cm.setAcceptCookie(true);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            cm.setAcceptThirdPartyCookies(wv, true);
        }

        wv.addJavascriptInterface(new FrostyBridge(), "FrostyNative");

        wv.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request != null ? request.getUrl() : null;
                return handleUri(uri);
            }

            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                if (url != null) {
                    lastLoadedUrl = url;
                    updateReturnPillVisibility(url);
                }
                offlineOverlay.setVisibility(View.GONE);
                topProgress.setVisibility(View.VISIBLE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                if (url != null) {
                    lastLoadedUrl = url;
                    updateReturnPillVisibility(url);
                }
                topProgress.setVisibility(View.GONE);
                dismissSplash();
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                if (request == null || !request.isForMainFrame()) return;
                int code = (error != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.M)
                        ? error.getErrorCode() : WebViewClient.ERROR_UNKNOWN;
                boolean isRealNetworkFailure =
                        !isNetworkAvailable()
                                || code == WebViewClient.ERROR_HOST_LOOKUP
                                || code == WebViewClient.ERROR_CONNECT
                                || code == WebViewClient.ERROR_TIMEOUT
                                || code == WebViewClient.ERROR_IO
                                || code == WebViewClient.ERROR_FAILED_SSL_HANDSHAKE;
                if (isRealNetworkFailure) {
                    dismissSplash();
                    offlineOverlay.setVisibility(View.VISIBLE);
                }
            }

            @Override
            public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                // Gracefully recover if Android OOM-kills WebGL renderer in 3D Stadium instead of freezing black
                if (root != null && webView != null) {
                    root.removeView(webView);
                    try {
                        webView.destroy();
                    } catch (Exception ignored) {
                    }
                    webView = createConfiguredWebView();
                    root.addView(webView, 0);
                    webView.loadUrl(lastLoadedUrl != null ? lastLoadedUrl : PACKS_URL);
                }
                return true;
            }
        });

        wv.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                topProgress.setProgress(newProgress);
                if (newProgress >= 65) {
                    dismissSplash();
                }
                if (newProgress >= 100) {
                    topProgress.setVisibility(View.GONE);
                }
            }

            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, Message resultMsg) {
                // Handle target="_blank" links cleanly (Presale, Fullscreen Stadium, external wallets)
                WebView transportView = new WebView(MainActivity.this);
                transportView.setWebViewClient(new WebViewClient() {
                    @Override
                    public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest req) {
                        Uri u = req != null ? req.getUrl() : null;
                        if (u != null) {
                            if (isFirstPartyUri(u)) {
                                webView.loadUrl(u.toString());
                            } else {
                                openExternalUri(u);
                            }
                        }
                        try {
                            v.destroy();
                        } catch (Exception ignored) {
                        }
                        return true;
                    }
                });
                WebView.WebViewTransport transport = (WebView.WebViewTransport) resultMsg.obj;
                transport.setWebView(transportView);
                resultMsg.sendToTarget();
                return true;
            }

            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(() -> {
                    try {
                        request.grant(request.getResources());
                    } catch (Exception ignored) {
                        request.deny();
                    }
                });
            }

            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (filePathCallback != null) {
                    filePathCallback.onReceiveValue(null);
                }
                filePathCallback = callback;
                try {
                    Intent intent = params.createIntent();
                    startActivityForResult(intent, FILE_CHOOSER_REQ);
                    return true;
                } catch (Exception e) {
                    filePathCallback = null;
                    return false;
                }
            }
        });

        return wv;
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        String nextUrl = resolveInitialUrl(intent);
        if (webView != null && nextUrl != null) {
            lastLoadedUrl = nextUrl;
            webView.loadUrl(nextUrl);
        }
    }

    private boolean isFirstPartyUri(Uri uri) {
        if (uri == null) return false;
        String scheme = uri.getScheme() != null ? uri.getScheme().toLowerCase() : "";
        String host = uri.getHost() != null ? uri.getHost().toLowerCase() : "";
        return ("https".equals(scheme) || "http".equals(scheme)) &&
                (host.endsWith("frostrips.web.app")
                        || host.endsWith("frostyrips-stadium.web.app")
                        || host.endsWith("frostyrips-presale.web.app")
                        || host.endsWith("firebaseapp.com"));
    }

    private void openExternalUri(Uri uri) {
        try {
            Intent ext = new Intent(Intent.ACTION_VIEW, uri);
            startActivity(ext);
        } catch (Exception ignored) {
        }
    }

    private void updateReturnPillVisibility(String url) {
        if (returnToPacksPill == null || url == null) return;
        boolean onSubApp = url.contains("frostyrips-stadium.web.app")
                || url.contains("frostyrips-presale.web.app");
        runOnUiThread(() -> returnToPacksPill.setVisibility(onSubApp ? View.VISIBLE : View.GONE));
    }

    private String resolveInitialUrl(Intent intent) {
        if (intent != null && intent.getData() != null) {
            Uri data = intent.getData();
            String scheme = data.getScheme();
            if ("frostyrips".equalsIgnoreCase(scheme)) {
                String host = data.getHost();
                if ("stadium".equalsIgnoreCase(host)) {
                    return STADIUM_URL;
                }
                if ("presale".equalsIgnoreCase(host)) {
                    return PRESALE_URL;
                }
                String path = data.getPath() != null ? data.getPath() : "/";
                String query = data.getEncodedQuery();
                return "https://frostrips.web.app" + path
                        + (query != null ? "?" + query + "&app=android&v=" + APP_VERSION : "?app=android&v=" + APP_VERSION);
            }
            if (isFirstPartyUri(data)) {
                return data.toString();
            }
        }
        return PACKS_URL;
    }

    private boolean handleUri(Uri uri) {
        if (uri == null) return false;
        String scheme = uri.getScheme() != null ? uri.getScheme().toLowerCase() : "";
        String host = uri.getHost() != null ? uri.getHost().toLowerCase() : "";

        if ("frostyrips".equals(scheme)) {
            if ("stadium".equals(host)) {
                webView.loadUrl(STADIUM_URL);
            } else if ("presale".equals(host)) {
                webView.loadUrl(PRESALE_URL);
            } else {
                webView.loadUrl(PACKS_URL);
            }
            return true;
        }

        if (isFirstPartyUri(uri)) {
            return false;
        }

        openExternalUri(uri);
        return true;
    }

    private TextView buildReturnPill() {
        TextView pill = new TextView(this);
        pill.setText("← PACKS");
        pill.setTextColor(Color.parseColor("#041521"));
        pill.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        pill.setTypeface(Typeface.DEFAULT_BOLD);
        pill.setLetterSpacing(0.06f);
        pill.setPadding(dp(12), dp(6), dp(12), dp(6));

        GradientDrawable bg = new GradientDrawable(
                GradientDrawable.Orientation.LEFT_RIGHT,
                new int[]{Color.parseColor("#00FFF7"), Color.parseColor("#38BDF8")});
        bg.setCornerRadius(dp(999));
        bg.setStroke(dp(1), Color.parseColor("#040303"));
        pill.setBackground(bg);
        pill.setElevation(dp(8));

        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.gravity = Gravity.TOP | Gravity.START;
        lp.topMargin = dp(10);
        lp.leftMargin = dp(10);
        pill.setLayoutParams(lp);
        pill.setOnClickListener(v -> {
            if (webView != null) {
                webView.loadUrl(PACKS_URL);
            }
        });
        return pill;
    }

    private LinearLayout buildSplashView() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER);
        box.setLayoutParams(new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));

        GradientDrawable bg = new GradientDrawable(
                GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{Color.parseColor("#0A1A36"), Color.parseColor("#050A16"), Color.parseColor("#03060E")});
        box.setBackground(bg);

        ImageView icon = new ImageView(this);
        icon.setImageResource(R.mipmap.ic_launcher);
        LinearLayout.LayoutParams iconLp = new LinearLayout.LayoutParams(dp(116), dp(116));
        iconLp.bottomMargin = dp(20);
        icon.setLayoutParams(iconLp);
        box.addView(icon);

        TextView title = new TextView(this);
        title.setText("FROSTYRIPS");
        title.setTextColor(Color.parseColor("#FFE500"));
        title.setTextSize(TypedValue.COMPLEX_UNIT_SP, 30);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setLetterSpacing(0.14f);
        title.setGravity(Gravity.CENTER);
        box.addView(title);

        TextView sub = new TextView(this);
        sub.setText("FOIL PACKS  •  $FROSTY PRESALE  •  3D STADIUM");
        sub.setTextColor(Color.parseColor("#7DD3FC"));
        sub.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11);
        sub.setLetterSpacing(0.10f);
        sub.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams subLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        subLp.topMargin = dp(6);
        subLp.bottomMargin = dp(26);
        sub.setLayoutParams(subLp);
        box.addView(sub);

        ProgressBar spinner = new ProgressBar(this);
        spinner.setIndeterminate(true);
        box.addView(spinner);

        return box;
    }

    private LinearLayout buildOfflineView() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER);
        box.setPadding(dp(32), dp(32), dp(32), dp(32));
        box.setBackgroundColor(Color.parseColor("#050A16"));
        box.setLayoutParams(new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));

        TextView heading = new TextView(this);
        heading.setText("ICE STORM CONNECTION LOST");
        heading.setTextColor(Color.parseColor("#00E5FF"));
        heading.setTextSize(TypedValue.COMPLEX_UNIT_SP, 20);
        heading.setTypeface(Typeface.DEFAULT_BOLD);
        heading.setGravity(Gravity.CENTER);
        box.addView(heading);

        TextView body = new TextView(this);
        body.setText("Connect to Wi-Fi or mobile data to rip FrostyRips foil packs and enter the 3D Stadium.");
        body.setTextColor(Color.parseColor("#9EB4D4"));
        body.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        body.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams bodyLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        bodyLp.topMargin = dp(10);
        bodyLp.bottomMargin = dp(24);
        body.setLayoutParams(bodyLp);
        box.addView(body);

        Button retryBtn = new Button(this);
        retryBtn.setText("RETRY CONNECTION");
        retryBtn.setTextColor(Color.parseColor("#041521"));
        retryBtn.setTypeface(Typeface.DEFAULT_BOLD);
        GradientDrawable btnBg = new GradientDrawable(
                GradientDrawable.Orientation.LEFT_RIGHT,
                new int[]{Color.parseColor("#00FFF7"), Color.parseColor("#2CA0FF")});
        btnBg.setCornerRadius(dp(16));
        retryBtn.setBackground(btnBg);
        retryBtn.setPadding(dp(28), dp(14), dp(28), dp(14));
        retryBtn.setOnClickListener(v -> {
            offlineOverlay.setVisibility(View.GONE);
            webView.loadUrl(lastLoadedUrl != null ? lastLoadedUrl : PACKS_URL);
        });
        box.addView(retryBtn);

        return box;
    }

    private Drawable createProgressDrawable() {
        GradientDrawable d = new GradientDrawable(
                GradientDrawable.Orientation.LEFT_RIGHT,
                new int[]{Color.parseColor("#00FFF7"), Color.parseColor("#FFE500")});
        return new ClipDrawable(d, Gravity.START, ClipDrawable.HORIZONTAL);
    }

    private void dismissSplash() {
        if (splashDismissed || splashOverlay == null) return;
        splashDismissed = true;
        splashOverlay.animate()
                .alpha(0f)
                .setDuration(240)
                .withEndAction(() -> splashOverlay.setVisibility(View.GONE))
                .start();
    }

    private boolean isNetworkAvailable() {
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
            NetworkInfo info = cm != null ? cm.getActiveNetworkInfo() : null;
            return info != null && info.isConnected();
        } catch (Exception e) {
            return true;
        }
    }

    private int dp(int value) {
        return Math.round(TypedValue.applyDimension(
                TypedValue.COMPLEX_UNIT_DIP, value, getResources().getDisplayMetrics()));
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILE_CHOOSER_REQ && filePathCallback != null) {
            Uri[] results = WebChromeClient.FileChooserParams.parseResult(resultCode, data);
            filePathCallback.onReceiveValue(results);
            filePathCallback = null;
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }
        long now = System.currentTimeMillis();
        if (now - lastBackPressMs < 1800) {
            super.onBackPressed();
        } else {
            lastBackPressMs = now;
            Toast.makeText(this, "Press back again to exit FrostyRips", Toast.LENGTH_SHORT).show();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (webView != null) webView.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) webView.onResume();
    }

    @Override
    protected void onDestroy() {
        mainHandler.removeCallbacksAndMessages(null);
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
    }

    private final class FrostyBridge {
        @JavascriptInterface
        public void vibrate(int durationMs) {
            try {
                Vibrator v = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
                if (v == null || !v.hasVibrator()) return;
                int clamped = Math.max(10, Math.min(350, durationMs));
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    v.vibrate(VibrationEffect.createOneShot(clamped, VibrationEffect.DEFAULT_AMPLITUDE));
                } else {
                    v.vibrate(clamped);
                }
            } catch (Exception ignored) {
            }
        }

        @JavascriptInterface
        public void share(String title, String text, String url) {
            runOnUiThread(() -> {
                try {
                    Intent i = new Intent(Intent.ACTION_SEND);
                    i.setType("text/plain");
                    i.putExtra(Intent.EXTRA_SUBJECT, title != null ? title : "FrostyRips");
                    String payload = (text != null ? text + "\n" : "") + (url != null ? url : PACKS_URL);
                    i.putExtra(Intent.EXTRA_TEXT, payload);
                    startActivity(Intent.createChooser(i, "Share FrostyRips"));
                } catch (Exception ignored) {
                }
            });
        }

        @JavascriptInterface
        public void copyText(String text) {
            runOnUiThread(() -> {
                try {
                    ClipboardManager cb = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                    if (cb != null && text != null) {
                        cb.setPrimaryClip(ClipData.newPlainText("FrostyRips", text));
                        Toast.makeText(MainActivity.this, "Copied to clipboard!", Toast.LENGTH_SHORT).show();
                    }
                } catch (Exception ignored) {
                }
            });
        }

        @JavascriptInterface
        public void toast(String message) {
            runOnUiThread(() -> Toast.makeText(MainActivity.this, message, Toast.LENGTH_SHORT).show());
        }

        @JavascriptInterface
        public void openStadium() {
            runOnUiThread(() -> webView.loadUrl(STADIUM_URL));
        }

        @JavascriptInterface
        public void openPacks() {
            runOnUiThread(() -> webView.loadUrl(PACKS_URL));
        }

        @JavascriptInterface
        public void openPresale() {
            runOnUiThread(() -> webView.loadUrl(PRESALE_URL));
        }

        @JavascriptInterface
        public String getAppInfo() {
            return "{\"platform\":\"android\",\"version\":\"" + APP_VERSION + "\",\"package\":\"com.frostyrips.app\"}";
        }
    }
}
