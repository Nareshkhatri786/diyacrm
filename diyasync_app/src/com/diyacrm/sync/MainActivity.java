package com.diyacrm.sync;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {
    private static final int REQ_CODE_FOLDER = 9901;
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);

        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient());
        webView.addJavascriptInterface(new DiyaBridge(this), "DiyaBridge");
        webView.loadUrl("file:///android_asset/index.html");

        // Request notification permission on Android 13+
        if (Build.VERSION.SDK_INT >= 33) {
            try {
                if (checkSelfPermission("android.permission.POST_NOTIFICATIONS") != 0) {
                    requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"}, 101);
                }
            } catch (Exception ignored) {}
        }

        // Start background service if already logged in and configured
        SharedPreferences prefs = getSharedPreferences("DiyaSync_Prefs", Context.MODE_PRIVATE);
        if (prefs.getInt("user_id", 0) > 0 && !prefs.getString("folder_uri", "").isEmpty()) {
            SyncService.start(this);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) {
            webView.evaluateJavascript("if (window.checkInit) window.checkInit();", null);
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQ_CODE_FOLDER && resultCode == RESULT_OK && data != null) {
            Uri uri = data.getData();
            if (uri != null) {
                try {
                    int takeFlags = data.getFlags() & (Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
                    getContentResolver().takePersistableUriPermission(uri, takeFlags != 0 ? takeFlags : Intent.FLAG_GRANT_READ_URI_PERMISSION);
                } catch (Exception ignored) {}

                SharedPreferences prefs = getSharedPreferences("DiyaSync_Prefs", Context.MODE_PRIVATE);
                prefs.edit().putString("folder_uri", uri.toString()).apply();

                Toast.makeText(this, "Recording folder linked successfully!", Toast.LENGTH_SHORT).show();

                // Start service & trigger immediate sync
                SyncService.start(this);
                new Thread(new Runnable() {
                    @Override
                    public void run() {
                        final int uploaded = SyncManager.performSync(MainActivity.this);
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                if (webView != null) {
                                    webView.evaluateJavascript("if (window.onSyncFinished) window.onSyncFinished(" + uploaded + ");", null);
                                }
                            }
                        });
                    }
                }).start();

                if (webView != null) {
                    webView.evaluateJavascript("if (window.checkInit) window.checkInit();", null);
                }
            }
        }
    }

    public class DiyaBridge {
        private final Context context;

        public DiyaBridge(Context c) {
            this.context = c;
        }

        @JavascriptInterface
        public String getAuthInfo() {
            SharedPreferences prefs = context.getSharedPreferences("DiyaSync_Prefs", Context.MODE_PRIVATE);
            int userId = prefs.getInt("user_id", 0);
            String folder = prefs.getString("folder_uri", "");
            SyncDbHelper db = new SyncDbHelper(context);

            JSONObject obj = new JSONObject();
            try {
                obj.put("isLoggedIn", userId > 0);
                obj.put("userId", userId);
                obj.put("userName", prefs.getString("user_name", ""));
                obj.put("companyId", prefs.getInt("company_id", 0));
                obj.put("companyName", prefs.getString("company_name", ""));
                obj.put("serverUrl", prefs.getString("server_url", "https://crm.sigprop.in"));
                obj.put("hasFolder", folder != null && !folder.isEmpty());
                obj.put("syncCount", db.getSyncedCount());
            } catch (Exception ignored) {}
            return obj.toString();
        }

        @JavascriptInterface
        public void login(final String serverUrl, final String username, final String password) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    try {
                        String endpoint = serverUrl.replaceAll("/+$", "") + "/api/call_tracker/login";
                        URL url = new URL(endpoint);
                        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                        conn.setRequestMethod("POST");
                        conn.setRequestProperty("Content-Type", "application/json");
                        conn.setConnectTimeout(10000);
                        conn.setReadTimeout(15000);
                        conn.setDoOutput(true);

                        JSONObject params = new JSONObject();
                        params.put("login", username);
                        params.put("password", password);

                        JSONObject rpc = new JSONObject();
                        rpc.put("jsonrpc", "2.0");
                        rpc.put("method", "call");
                        rpc.put("params", params);
                        rpc.put("id", 1);

                        OutputStream os = conn.getOutputStream();
                        os.write(rpc.toString().getBytes("UTF-8"));
                        os.close();

                        int respCode = conn.getResponseCode();
                        if (respCode == 200) {
                            BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                            StringBuilder sb = new StringBuilder();
                            String line;
                            while ((line = br.readLine()) != null) sb.append(line);
                            br.close();

                            JSONObject res = new JSONObject(sb.toString());
                            if (res.has("result")) {
                                JSONObject result = res.getJSONObject("result");
                                if ("success".equals(result.optString("status"))) {
                                    SharedPreferences prefs = context.getSharedPreferences("DiyaSync_Prefs", Context.MODE_PRIVATE);
                                    prefs.edit()
                                            .putString("server_url", serverUrl)
                                            .putInt("user_id", result.getInt("user_id"))
                                            .putString("user_name", result.getString("user_name"))
                                            .putInt("company_id", result.getInt("company_id"))
                                            .putString("company_name", result.getString("company_name"))
                                            .apply();

                                    runOnUiThread(new Runnable() {
                                        @Override
                                        public void run() {
                                            if (webView != null) {
                                                webView.evaluateJavascript("if (window.onLoginSuccess) window.onLoginSuccess();", null);
                                            }
                                        }
                                    });
                                    return;
                                } else {
                                    final String msg = result.optString("message", "Login failed");
                                    notifyLoginFail(msg);
                                    return;
                                }
                            }
                        }
                        notifyLoginFail("Server returned HTTP " + respCode);
                    } catch (Exception e) {
                        notifyLoginFail("Connection error: " + e.getMessage());
                    }
                }
            }).start();
        }

        private void notifyLoginFail(final String msg) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (webView != null) {
                        webView.evaluateJavascript("if (window.onLoginFailed) window.onLoginFailed('" + msg.replace("'", "\\'") + "');", null);
                    }
                }
            });
        }

        @JavascriptInterface
        public void logout() {
            SharedPreferences prefs = context.getSharedPreferences("DiyaSync_Prefs", Context.MODE_PRIVATE);
            prefs.edit().clear().apply();
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (webView != null) {
                        webView.evaluateJavascript("if (window.checkInit) window.checkInit();", null);
                    }
                }
            });
        }

        @JavascriptInterface
        public void pickFolder() {
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
            startActivityForResult(intent, REQ_CODE_FOLDER);
        }

        @JavascriptInterface
        public void syncNow() {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    final int uploaded = SyncManager.performSync(context);
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            if (webView != null) {
                                webView.evaluateJavascript("if (window.onSyncFinished) window.onSyncFinished(" + uploaded + ");", null);
                            }
                        }
                    });
                }
            }).start();
        }

        @JavascriptInterface
        public String getRecentLogs() {
            SyncDbHelper db = new SyncDbHelper(context);
            return db.getRecentLogsJson();
        }
    }
}
