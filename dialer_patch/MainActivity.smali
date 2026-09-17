.class public Lcom/diyacrm/dialer/MainActivity;
.super Landroid/app/Activity;
.source "MainActivity.java"


# annotations
.annotation system Ldalvik/annotation/MemberClasses;
    value = {
        Lcom/diyacrm/dialer/MainActivity$WebAppInterface;
    }
.end annotation


# static fields
.field private static final PERM_REQ_CODE:I = 0x3e9


# instance fields
.field private webView:Landroid/webkit/WebView;


# direct methods
.method public static synthetic $r8$lambda$8plCBJo0s7D9EZFtJxNuSMr65EI(Lcom/diyacrm/dialer/MainActivity;ZLjava/lang/String;Ljava/lang/String;I)V
    .locals 0

    invoke-direct {p0, p1, p2, p3, p4}, Lcom/diyacrm/dialer/MainActivity;->lambda$refreshUI$0(ZLjava/lang/String;Ljava/lang/String;I)V

    return-void
.end method

.method static bridge synthetic -$$Nest$mrefreshUI(Lcom/diyacrm/dialer/MainActivity;)V
    .locals 0

    invoke-direct {p0}, Lcom/diyacrm/dialer/MainActivity;->refreshUI()V

    return-void
.end method

.method public constructor <init>()V
    .locals 0

    .line 27
    invoke-direct {p0}, Landroid/app/Activity;-><init>()V

    return-void
.end method

.method private checkAndRequestPermissions()V
    .locals 11

    .line 66
    :try_start_0
    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    const/16 v1, 0x21

    const-string v2, "android.permission.CALL_PHONE"

    const/4 v3, 0x2

    const-string v4, "android.permission.READ_PHONE_STATE"

    const-string v5, "android.permission.READ_CALL_LOG"

    const-string v9, "android.permission.RECORD_AUDIO"

    const/4 v6, 0x3

    const/4 v10, 0x4

    const/4 v7, 0x1

    const/4 v8, 0x0

    if-lt v0, v1, :cond_0

    .line 67
    const/4 v0, 0x6

    :try_start_1
    new-array v0, v0, [Ljava/lang/String;

    aput-object v5, v0, v8

    aput-object v4, v0, v7

    aput-object v2, v0, v3

    aput-object v9, v0, v6

    const-string v1, "android.permission.POST_NOTIFICATIONS"

    aput-object v1, v0, v10

    const/4 v1, 0x5

    const-string v2, "android.permission.READ_EXTERNAL_STORAGE"

    aput-object v2, v0, v1

    .local v0, "perms":[Ljava/lang/String;
    goto :goto_0

    .line 74
    .end local v0    # "perms":[Ljava/lang/String;
    :cond_0
    const/4 v0, 0x5

    new-array v0, v0, [Ljava/lang/String;

    aput-object v5, v0, v8

    aput-object v4, v0, v7

    aput-object v2, v0, v3

    aput-object v9, v0, v6

    const-string v1, "android.permission.READ_EXTERNAL_STORAGE"

    aput-object v1, v0, v10

    .line 81
    .restart local v0    # "perms":[Ljava/lang/String;
    :goto_0
    const/4 v1, 0x1

    .line 82
    .local v1, "allGranted":Z
    array-length v2, v0

    :goto_1
    if-ge v8, v2, :cond_2

    aget-object v3, v0, v8

    .line 83
    .local v3, "p":Ljava/lang/String;
    invoke-static {p0, v3}, Landroidx/core/content/ContextCompat;->checkSelfPermission(Landroid/content/Context;Ljava/lang/String;)I

    move-result v4

    if-eqz v4, :cond_1

    .line 84
    const/4 v1, 0x0

    .line 85
    goto :goto_2

    .line 82
    .end local v3    # "p":Ljava/lang/String;
    :cond_1
    add-int/lit8 v8, v8, 0x1

    goto :goto_1

    .line 89
    :cond_2
    :goto_2
    if-nez v1, :cond_3

    .line 90
    const/16 v2, 0x3e9

    invoke-static {p0, v0, v2}, Landroidx/core/app/ActivityCompat;->requestPermissions(Landroid/app/Activity;[Ljava/lang/String;I)V
    :try_end_1
    .catch Ljava/lang/Exception; {:try_start_1 .. :try_end_1} :catch_0

    goto :goto_3

    .line 92
    .end local v0    # "perms":[Ljava/lang/String;
    .end local v1    # "allGranted":Z
    :catch_0
    move-exception v0

    :cond_3
    :goto_3
    nop

    .line 93
    return-void
.end method

.method private synthetic lambda$refreshUI$0(ZLjava/lang/String;Ljava/lang/String;I)V
    .locals 3
    .param p1, "isLoggedIn"    # Z
    .param p2, "name"    # Ljava/lang/String;
    .param p3, "comp"    # Ljava/lang/String;
    .param p4, "unsynced"    # I

    .line 235
    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity;->webView:Landroid/webkit/WebView;

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "updateUIState("

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1, p1}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v2, ", \'"

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v2, "\', \'"

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1, p3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v2, "\', "

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1, p4}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v2, ");"

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    const/4 v2, 0x0

    invoke-virtual {v0, v1, v2}, Landroid/webkit/WebView;->evaluateJavascript(Ljava/lang/String;Landroid/webkit/ValueCallback;)V

    .line 236
    return-void
.end method

.method private refreshUI()V
    .locals 10

    .line 227
    const-string v0, ""

    :try_start_0
    const-string v1, "DiyaCRM_Prefs"

    const/4 v2, 0x0

    invoke-virtual {p0, v1, v2}, Lcom/diyacrm/dialer/MainActivity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v1

    .line 228
    .local v1, "prefs":Landroid/content/SharedPreferences;
    const-string v3, "user_id"

    invoke-interface {v1, v3, v2}, Landroid/content/SharedPreferences;->getInt(Ljava/lang/String;I)I

    move-result v3

    if-lez v3, :cond_0

    const/4 v2, 0x1

    :cond_0
    move v5, v2

    .line 229
    .local v5, "isLoggedIn":Z
    const-string v2, "user_name"

    invoke-interface {v1, v2, v0}, Landroid/content/SharedPreferences;->getString(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v6

    .line 230
    .local v6, "name":Ljava/lang/String;
    const-string v2, "company_name"

    invoke-interface {v1, v2, v0}, Landroid/content/SharedPreferences;->getString(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v7

    .line 231
    .local v7, "comp":Ljava/lang/String;
    new-instance v0, Lcom/diyacrm/dialer/OfflineDbHelper;

    invoke-direct {v0, p0}, Lcom/diyacrm/dialer/OfflineDbHelper;-><init>(Landroid/content/Context;)V

    .line 232
    .local v0, "db":Lcom/diyacrm/dialer/OfflineDbHelper;
    invoke-virtual {v0}, Lcom/diyacrm/dialer/OfflineDbHelper;->getUnsyncedCount()I

    move-result v8

    .line 234
    .local v8, "unsynced":I
    iget-object v2, p0, Lcom/diyacrm/dialer/MainActivity;->webView:Landroid/webkit/WebView;

    new-instance v9, Lcom/diyacrm/dialer/MainActivity$$ExternalSyntheticLambda0;

    move-object v3, v9

    move-object v4, p0

    invoke-direct/range {v3 .. v8}, Lcom/diyacrm/dialer/MainActivity$$ExternalSyntheticLambda0;-><init>(Lcom/diyacrm/dialer/MainActivity;ZLjava/lang/String;Ljava/lang/String;I)V

    invoke-virtual {v2, v9}, Landroid/webkit/WebView;->post(Ljava/lang/Runnable;)Z
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    .line 237
    nop

    .end local v0    # "db":Lcom/diyacrm/dialer/OfflineDbHelper;
    .end local v1    # "prefs":Landroid/content/SharedPreferences;
    .end local v5    # "isLoggedIn":Z
    .end local v6    # "name":Ljava/lang/String;
    .end local v7    # "comp":Ljava/lang/String;
    .end local v8    # "unsynced":I
    goto :goto_0

    :catch_0
    move-exception v0

    .line 238
    :goto_0
    return-void
.end method


# virtual methods
.method protected onCreate(Landroid/os/Bundle;)V
    .locals 5
    .param p1, "savedInstanceState"    # Landroid/os/Bundle;

    .line 33
    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V

    .line 36
    const/4 v0, 0x1

    :try_start_0
    new-instance v1, Landroid/webkit/WebView;

    invoke-direct {v1, p0}, Landroid/webkit/WebView;-><init>(Landroid/content/Context;)V

    iput-object v1, p0, Lcom/diyacrm/dialer/MainActivity;->webView:Landroid/webkit/WebView;

    .line 37
    iget-object v1, p0, Lcom/diyacrm/dialer/MainActivity;->webView:Landroid/webkit/WebView;

    invoke-virtual {p0, v1}, Lcom/diyacrm/dialer/MainActivity;->setContentView(Landroid/view/View;)V

    .line 39
    iget-object v1, p0, Lcom/diyacrm/dialer/MainActivity;->webView:Landroid/webkit/WebView;

    invoke-virtual {v1}, Landroid/webkit/WebView;->getSettings()Landroid/webkit/WebSettings;

    move-result-object v1

    .line 40
    .local v1, "settings":Landroid/webkit/WebSettings;
    invoke-virtual {v1, v0}, Landroid/webkit/WebSettings;->setJavaScriptEnabled(Z)V

    .line 41
    invoke-virtual {v1, v0}, Landroid/webkit/WebSettings;->setDomStorageEnabled(Z)V

    .line 42
    invoke-virtual {v1, v0}, Landroid/webkit/WebSettings;->setAllowFileAccess(Z)V

    .line 43
    invoke-virtual {v1, v0}, Landroid/webkit/WebSettings;->setAllowContentAccess(Z)V

    .line 45
    iget-object v2, p0, Lcom/diyacrm/dialer/MainActivity;->webView:Landroid/webkit/WebView;

    new-instance v3, Landroid/webkit/WebChromeClient;

    invoke-direct {v3}, Landroid/webkit/WebChromeClient;-><init>()V

    invoke-virtual {v2, v3}, Landroid/webkit/WebView;->setWebChromeClient(Landroid/webkit/WebChromeClient;)V

    .line 46
    iget-object v2, p0, Lcom/diyacrm/dialer/MainActivity;->webView:Landroid/webkit/WebView;

    new-instance v3, Lcom/diyacrm/dialer/MainActivity$1;

    invoke-direct {v3, p0}, Lcom/diyacrm/dialer/MainActivity$1;-><init>(Lcom/diyacrm/dialer/MainActivity;)V

    invoke-virtual {v2, v3}, Landroid/webkit/WebView;->setWebViewClient(Landroid/webkit/WebViewClient;)V

    .line 54
    iget-object v2, p0, Lcom/diyacrm/dialer/MainActivity;->webView:Landroid/webkit/WebView;

    new-instance v3, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;

    invoke-direct {v3, p0, p0}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;-><init>(Lcom/diyacrm/dialer/MainActivity;Landroid/content/Context;)V

    const-string v4, "AndroidBridge"

    invoke-virtual {v2, v3, v4}, Landroid/webkit/WebView;->addJavascriptInterface(Ljava/lang/Object;Ljava/lang/String;)V

    .line 55
    iget-object v2, p0, Lcom/diyacrm/dialer/MainActivity;->webView:Landroid/webkit/WebView;

    const-string v3, "file:///android_asset/index.html"

    invoke-virtual {v2, v3}, Landroid/webkit/WebView;->loadUrl(Ljava/lang/String;)V

    .line 57
    invoke-direct {p0}, Lcom/diyacrm/dialer/MainActivity;->checkAndRequestPermissions()V
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    .line 60
    .end local v1    # "settings":Landroid/webkit/WebSettings;
    goto :goto_0

    .line 58
    :catch_0
    move-exception v1

    .line 59
    .local v1, "e":Ljava/lang/Exception;
    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "Init Error: "

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v1}, Ljava/lang/Exception;->getMessage()Ljava/lang/String;

    move-result-object v3

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    invoke-static {p0, v2, v0}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;

    move-result-object v0

    invoke-virtual {v0}, Landroid/widget/Toast;->show()V

    .line 61
    .end local v1    # "e":Ljava/lang/Exception;
    :goto_0
    return-void
.end method

.method protected onResume()V
    .locals 4

    .line 242
    invoke-super {p0}, Landroid/app/Activity;->onResume()V

    :try_start_res
    const-string v0, "DiyaCRM_Prefs"

    const/4 v1, 0x0

    invoke-virtual {p0, v0, v1}, Lcom/diyacrm/dialer/MainActivity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    new-instance v1, Lcom/diyacrm/dialer/OfflineDbHelper;

    invoke-direct {v1, p0}, Lcom/diyacrm/dialer/OfflineDbHelper;-><init>(Landroid/content/Context;)V

    # fetchRecentCallsFromDevice is pure DB - safe on main thread
    invoke-static {p0, v0, v1}, Lcom/diyacrm/dialer/SyncManager;->fetchRecentCallsFromDevice(Landroid/content/Context;Landroid/content/SharedPreferences;Lcom/diyacrm/dialer/OfflineDbHelper;)V

    # syncPendingCalls does network - must run on background thread
    new-instance v2, Ljava/lang/Thread;

    new-instance v3, Lcom/diyacrm/dialer/SyncManager$$ExternalSyntheticLambda0;

    invoke-direct {v3, p0}, Lcom/diyacrm/dialer/SyncManager$$ExternalSyntheticLambda0;-><init>(Landroid/content/Context;)V

    invoke-direct {v2, v3}, Ljava/lang/Thread;-><init>(Ljava/lang/Runnable;)V

    invoke-virtual {v2}, Ljava/lang/Thread;->start()V

    :try_end_res
    .catch Ljava/lang/Exception; {:try_start_res .. :try_end_res} :catch_res

    :catch_res
    .line 243
    invoke-direct {p0}, Lcom/diyacrm/dialer/MainActivity;->refreshUI()V

    .line 244
    return-void
.end method

.method protected onActivityResult(IILandroid/content/Intent;)V
    .locals 4
    .param p1, "requestCode"    # I
    .param p2, "resultCode"    # I
    .param p3, "data"    # Landroid/content/Intent;

    invoke-super {p0, p1, p2, p3}, Landroid/app/Activity;->onActivityResult(IILandroid/content/Intent;)V

    const/16 v0, 0x26ad

    if-ne p1, v0, :cond_exit

    const/4 v0, -0x1

    if-ne p2, v0, :cond_exit

    if-eqz p3, :cond_exit

    invoke-virtual {p3}, Landroid/content/Intent;->getData()Landroid/net/Uri;

    move-result-object v0

    if-eqz v0, :cond_exit

    :try_start_saf
    invoke-virtual {p0}, Lcom/diyacrm/dialer/MainActivity;->getContentResolver()Landroid/content/ContentResolver;

    move-result-object v1

    const/4 v2, 0x3

    invoke-virtual {v1, v0, v2}, Landroid/content/ContentResolver;->takePersistableUriPermission(Landroid/net/Uri;I)V
    :try_end_saf
    .catch Ljava/lang/Exception; {:try_start_saf .. :try_end_saf} :catch_saf

    :catch_saf
    const-string v1, "DiyaCRM_Prefs"

    const/4 v2, 0x0

    invoke-virtual {p0, v1, v2}, Lcom/diyacrm/dialer/MainActivity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v1

    invoke-interface {v1}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;

    move-result-object v1

    const-string v2, "recording_folder_uri"

    invoke-virtual {v0}, Landroid/net/Uri;->toString()Ljava/lang/String;

    move-result-object v3

    invoke-interface {v1, v2, v3}, Landroid/content/SharedPreferences$Editor;->putString(Ljava/lang/String;Ljava/lang/String;)Landroid/content/SharedPreferences$Editor;

    move-result-object v1

    invoke-interface {v1}, Landroid/content/SharedPreferences$Editor;->apply()V

    invoke-direct {p0}, Lcom/diyacrm/dialer/MainActivity;->refreshUI()V

    :cond_exit
    return-void
.end method
