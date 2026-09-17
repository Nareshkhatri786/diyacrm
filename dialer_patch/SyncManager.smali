.class public Lcom/diyacrm/dialer/SyncManager;
.super Ljava/lang/Object;
.source "SyncManager.java"


# static fields
.field private static final TAG:Ljava/lang/String; = "DiyaCRMSync"


# direct methods
.method public constructor <init>()V
    .locals 0

    .line 19
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method public static isNetworkAvailable(Landroid/content/Context;)Z
    .locals 5
    .param p0, "context"    # Landroid/content/Context;

    .line 23
    const-string v0, "connectivity"

    invoke-virtual {p0, v0}, Landroid/content/Context;->getSystemService(Ljava/lang/String;)Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Landroid/net/ConnectivityManager;

    .line 24
    .local v0, "cm":Landroid/net/ConnectivityManager;
    const/4 v1, 0x0

    if-nez v0, :cond_0

    return v1

    .line 25
    :cond_0
    invoke-virtual {v0}, Landroid/net/ConnectivityManager;->getActiveNetwork()Landroid/net/Network;

    move-result-object v2

    invoke-virtual {v0, v2}, Landroid/net/ConnectivityManager;->getNetworkCapabilities(Landroid/net/Network;)Landroid/net/NetworkCapabilities;

    move-result-object v2

    .line 26
    .local v2, "nc":Landroid/net/NetworkCapabilities;
    if-eqz v2, :cond_2

    const/4 v3, 0x1

    invoke-virtual {v2, v3}, Landroid/net/NetworkCapabilities;->hasTransport(I)Z

    move-result v4

    if-nez v4, :cond_1

    .line 27
    invoke-virtual {v2, v1}, Landroid/net/NetworkCapabilities;->hasTransport(I)Z

    move-result v4

    if-eqz v4, :cond_2

    :cond_1
    move v1, v3

    goto :goto_0

    :cond_2
    nop

    .line 26
    :goto_0
    return v1
.end method

.method static synthetic lambda$syncPendingCalls$0(Landroid/content/Context;)V
    .locals 26
    .param p0, "context"    # Landroid/content/Context;

    .line 37
    move-object/from16 v0, p0

    const-string v1, "DiyaCRM_Prefs"

    const/4 v2, 0x0

    invoke-virtual {v0, v1, v2}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v1

    .line 38
    .local v1, "prefs":Landroid/content/SharedPreferences;
    const-string v3, "server_url"

    const-string v4, "https://crm.sigprop.in"

    invoke-interface {v1, v3, v4}, Landroid/content/SharedPreferences;->getString(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v3

    .line 39
    .local v3, "serverUrl":Ljava/lang/String;
    const-string v4, "user_id"

    invoke-interface {v1, v4, v2}, Landroid/content/SharedPreferences;->getInt(Ljava/lang/String;I)I

    move-result v12

    .line 40
    .local v12, "userId":I
    const-string v13, "company_id"

    invoke-interface {v1, v13, v2}, Landroid/content/SharedPreferences;->getInt(Ljava/lang/String;I)I

    move-result v2

    .line 42
    .local v2, "companyId":I
    const-string v14, "DiyaCRMSync"

    if-nez v12, :cond_0

    .line 43
    const-string v4, "No user logged in, skipping sync."

    invoke-static {v14, v4}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    .line 44
    return-void

    .line 47
    :cond_0
    new-instance v5, Lcom/diyacrm/dialer/OfflineDbHelper;

    invoke-direct {v5, v0}, Lcom/diyacrm/dialer/OfflineDbHelper;-><init>(Landroid/content/Context;)V

    move-object v15, v5

    invoke-static {v0, v1, v15}, Lcom/diyacrm/dialer/SyncManager;->fetchRecentCallsFromDevice(Landroid/content/Context;Landroid/content/SharedPreferences;Lcom/diyacrm/dialer/OfflineDbHelper;)V

    .line 48
    .local v15, "db":Lcom/diyacrm/dialer/OfflineDbHelper;
    invoke-virtual {v15}, Lcom/diyacrm/dialer/OfflineDbHelper;->getReadableDatabase()Landroid/database/sqlite/SQLiteDatabase;

    move-result-object v11

    .line 49
    .local v11, "rdb":Landroid/database/sqlite/SQLiteDatabase;
    const-string v5, "SELECT * FROM pending_calls WHERE synced = 0"

    const/4 v6, 0x0

    invoke-virtual {v11, v5, v6}, Landroid/database/sqlite/SQLiteDatabase;->rawQuery(Ljava/lang/String;[Ljava/lang/String;)Landroid/database/Cursor;

    move-result-object v10

    .line 51
    .local v10, "c":Landroid/database/Cursor;
    invoke-interface {v10}, Landroid/database/Cursor;->moveToFirst()Z

    move-result v5

    if-eqz v5, :cond_5

    .line 53
    :goto_0
    const-string v5, "id"

    invoke-interface {v10, v5}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v5

    invoke-interface {v10, v5}, Landroid/database/Cursor;->getLong(I)J

    move-result-wide v8

    .line 54
    .local v8, "id":J
    const-string v5, "phone_number"

    invoke-interface {v10, v5}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v5

    invoke-interface {v10, v5}, Landroid/database/Cursor;->getString(I)Ljava/lang/String;

    move-result-object v16

    .line 55
    .local v16, "phone":Ljava/lang/String;
    const-string v5, "call_type"

    invoke-interface {v10, v5}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v5

    invoke-interface {v10, v5}, Landroid/database/Cursor;->getString(I)Ljava/lang/String;

    move-result-object v17

    .line 56
    .local v17, "type":Ljava/lang/String;
    const-string v5, "duration_seconds"

    invoke-interface {v10, v5}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v5

    invoke-interface {v10, v5}, Landroid/database/Cursor;->getInt(I)I

    move-result v18

    .line 57
    .local v18, "duration":I
    const-string v5, "start_time"

    invoke-interface {v10, v5}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v5

    invoke-interface {v10, v5}, Landroid/database/Cursor;->getString(I)Ljava/lang/String;

    move-result-object v19

    .line 58
    .local v19, "startTime":Ljava/lang/String;
    invoke-interface {v10, v4}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v5

    invoke-interface {v10, v5}, Landroid/database/Cursor;->getInt(I)I

    move-result v20

    .line 59
    .local v20, "recUserId":I
    invoke-interface {v10, v13}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v5

    invoke-interface {v10, v5}, Landroid/database/Cursor;->getInt(I)I

    move-result v21

    .line 61
    .local v21, "recCompanyId":I
    if-lez v20, :cond_1

    move/from16 v22, v20

    goto :goto_1

    :cond_1
    move/from16 v22, v12

    :goto_1
    if-lez v21, :cond_2

    move/from16 v23, v21

    goto :goto_2

    :cond_2
    move/from16 v23, v2

    :goto_2
    move-object v5, v3

    move-object/from16 v6, v16

    move-object/from16 v7, v17

    move-object/from16 v24, v1

    move-wide v0, v8

    .end local v1    # "prefs":Landroid/content/SharedPreferences;
    .end local v8    # "id":J
    .local v0, "id":J
    .local v24, "prefs":Landroid/content/SharedPreferences;
    move/from16 v8, v18

    move-object/from16 v9, v19

    move-object/from16 v25, v10

    .end local v10    # "c":Landroid/database/Cursor;
    .local v25, "c":Landroid/database/Cursor;
    move/from16 v10, v22

    move-object/from16 v22, v11

    .end local v11    # "rdb":Landroid/database/sqlite/SQLiteDatabase;
    .local v22, "rdb":Landroid/database/sqlite/SQLiteDatabase;
    move/from16 v11, v23

    invoke-static/range {v5 .. v11}, Lcom/diyacrm/dialer/SyncManager;->sendCallToOdoo(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;ILjava/lang/String;II)Z

    move-result v5

    .line 62
    .local v5, "success":Z
    if-eqz v5, :cond_3

    .line 63
    invoke-virtual {v15, v0, v1}, Lcom/diyacrm/dialer/OfflineDbHelper;->markAsSynced(J)V

    .line 64
    new-instance v6, Ljava/lang/StringBuilder;

    invoke-direct {v6}, Ljava/lang/StringBuilder;-><init>()V

    const-string v7, "Call #"

    invoke-virtual {v6, v7}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v6

    invoke-virtual {v6, v0, v1}, Ljava/lang/StringBuilder;->append(J)Ljava/lang/StringBuilder;

    move-result-object v6

    const-string v7, " Synced successfully to Odoo!"

    invoke-virtual {v6, v7}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v6

    invoke-virtual {v6}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v6

    invoke-static {v14, v6}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    .line 66
    .end local v0    # "id":J
    .end local v5    # "success":Z
    .end local v16    # "phone":Ljava/lang/String;
    .end local v17    # "type":Ljava/lang/String;
    .end local v18    # "duration":I
    .end local v19    # "startTime":Ljava/lang/String;
    .end local v20    # "recUserId":I
    .end local v21    # "recCompanyId":I
    :cond_3
    invoke-interface/range {v25 .. v25}, Landroid/database/Cursor;->moveToNext()Z

    move-result v0

    if-nez v0, :cond_4

    goto :goto_3

    :cond_4
    move-object/from16 v0, p0

    move-object/from16 v11, v22

    move-object/from16 v1, v24

    move-object/from16 v10, v25

    goto/16 :goto_0

    .line 51
    .end local v22    # "rdb":Landroid/database/sqlite/SQLiteDatabase;
    .end local v24    # "prefs":Landroid/content/SharedPreferences;
    .end local v25    # "c":Landroid/database/Cursor;
    .restart local v1    # "prefs":Landroid/content/SharedPreferences;
    .restart local v10    # "c":Landroid/database/Cursor;
    .restart local v11    # "rdb":Landroid/database/sqlite/SQLiteDatabase;
    :cond_5
    move-object/from16 v24, v1

    move-object/from16 v25, v10

    move-object/from16 v22, v11

    .line 68
    .end local v1    # "prefs":Landroid/content/SharedPreferences;
    .end local v10    # "c":Landroid/database/Cursor;
    .end local v11    # "rdb":Landroid/database/sqlite/SQLiteDatabase;
    .restart local v22    # "rdb":Landroid/database/sqlite/SQLiteDatabase;
    .restart local v24    # "prefs":Landroid/content/SharedPreferences;
    .restart local v25    # "c":Landroid/database/Cursor;
    :goto_3
    invoke-interface/range {v25 .. v25}, Landroid/database/Cursor;->close()V

    .line 69
    return-void
.end method

.method private static sendCallToOdoo(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;ILjava/lang/String;II)Z
    .locals 21
    .param p0, "serverUrl"    # Ljava/lang/String;
    .param p1, "phone"    # Ljava/lang/String;
    .param p2, "type"    # Ljava/lang/String;
    .param p3, "duration"    # I
    .param p4, "startTime"    # Ljava/lang/String;
    .param p5, "userId"    # I
    .param p6, "companyId"    # I

    .line 74
    const-string v0, "result"

    :try_start_0
    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "/+$"

    const-string v3, ""
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_7

    move-object/from16 v4, p0

    :try_start_1
    invoke-virtual {v4, v2, v3}, Ljava/lang/String;->replaceAll(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v2

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v2, "/api/call_tracker/sync_call"

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    .line 75
    .local v1, "endpoint":Ljava/lang/String;
    new-instance v2, Ljava/net/URL;

    invoke-direct {v2, v1}, Ljava/net/URL;-><init>(Ljava/lang/String;)V

    .line 76
    .local v2, "url":Ljava/net/URL;
    invoke-virtual {v2}, Ljava/net/URL;->openConnection()Ljava/net/URLConnection;

    move-result-object v3

    check-cast v3, Ljava/net/HttpURLConnection;

    .line 77
    .local v3, "conn":Ljava/net/HttpURLConnection;
    const-string v5, "POST"

    invoke-virtual {v3, v5}, Ljava/net/HttpURLConnection;->setRequestMethod(Ljava/lang/String;)V

    .line 78
    const-string v5, "Content-Type"

    const-string v6, "application/json"

    invoke-virtual {v3, v5, v6}, Ljava/net/HttpURLConnection;->setRequestProperty(Ljava/lang/String;Ljava/lang/String;)V

    .line 79
    const/16 v5, 0x2710

    invoke-virtual {v3, v5}, Ljava/net/HttpURLConnection;->setConnectTimeout(I)V

    .line 80
    invoke-virtual {v3, v5}, Ljava/net/HttpURLConnection;->setReadTimeout(I)V

    .line 81
    const/4 v5, 0x1

    invoke-virtual {v3, v5}, Ljava/net/HttpURLConnection;->setDoOutput(Z)V

    .line 83
    new-instance v5, Lorg/json/JSONObject;

    invoke-direct {v5}, Lorg/json/JSONObject;-><init>()V

    .line 84
    .local v5, "params":Lorg/json/JSONObject;
    const-string v6, "phone_number"
    :try_end_1
    .catch Ljava/lang/Exception; {:try_start_1 .. :try_end_1} :catch_6

    move-object/from16 v7, p1

    :try_start_2
    invoke-virtual {v5, v6, v7}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    .line 85
    const-string v6, "call_type"
    :try_end_2
    .catch Ljava/lang/Exception; {:try_start_2 .. :try_end_2} :catch_5

    move-object/from16 v8, p2

    :try_start_3
    invoke-virtual {v5, v6, v8}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    .line 86
    const-string v6, "duration_seconds"
    :try_end_3
    .catch Ljava/lang/Exception; {:try_start_3 .. :try_end_3} :catch_4

    move/from16 v9, p3

    :try_start_4
    invoke-virtual {v5, v6, v9}, Lorg/json/JSONObject;->put(Ljava/lang/String;I)Lorg/json/JSONObject;

    .line 87
    const-string v6, "start_time"
    :try_end_4
    .catch Ljava/lang/Exception; {:try_start_4 .. :try_end_4} :catch_3

    move-object/from16 v10, p4

    :try_start_5
    invoke-virtual {v5, v6, v10}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    .line 88
    const-string v6, "user_id"
    :try_end_5
    .catch Ljava/lang/Exception; {:try_start_5 .. :try_end_5} :catch_2

    move/from16 v11, p5

    :try_start_6
    invoke-virtual {v5, v6, v11}, Lorg/json/JSONObject;->put(Ljava/lang/String;I)Lorg/json/JSONObject;

    .line 89
    const-string v6, "company_id"
    :try_end_6
    .catch Ljava/lang/Exception; {:try_start_6 .. :try_end_6} :catch_1

    move/from16 v12, p6

    :try_start_7
    invoke-virtual {v5, v6, v12}, Lorg/json/JSONObject;->put(Ljava/lang/String;I)Lorg/json/JSONObject;

    .line 91
    new-instance v6, Lorg/json/JSONObject;

    invoke-direct {v6}, Lorg/json/JSONObject;-><init>()V

    .line 92
    .local v6, "rpc":Lorg/json/JSONObject;
    const-string v13, "jsonrpc"

    const-string v14, "2.0"

    invoke-virtual {v6, v13, v14}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    .line 93
    const-string v13, "method"

    const-string v14, "call"

    invoke-virtual {v6, v13, v14}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    .line 94
    const-string v13, "params"

    invoke-virtual {v6, v13, v5}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    .line 95
    const-string v13, "id"

    invoke-static {}, Ljava/lang/System;->currentTimeMillis()J

    move-result-wide v14

    invoke-virtual {v6, v13, v14, v15}, Lorg/json/JSONObject;->put(Ljava/lang/String;J)Lorg/json/JSONObject;

    .line 97
    invoke-virtual {v3}, Ljava/net/HttpURLConnection;->getOutputStream()Ljava/io/OutputStream;

    move-result-object v13

    .line 98
    .local v13, "os":Ljava/io/OutputStream;
    invoke-virtual {v6}, Lorg/json/JSONObject;->toString()Ljava/lang/String;

    move-result-object v14

    const-string v15, "UTF-8"

    invoke-virtual {v14, v15}, Ljava/lang/String;->getBytes(Ljava/lang/String;)[B

    move-result-object v14

    invoke-virtual {v13, v14}, Ljava/io/OutputStream;->write([B)V

    .line 99
    invoke-virtual {v13}, Ljava/io/OutputStream;->close()V

    .line 101
    invoke-virtual {v3}, Ljava/net/HttpURLConnection;->getResponseCode()I

    move-result v14

    .line 102
    .local v14, "code":I
    const/16 v15, 0xc8

    if-ne v14, v15, :cond_2

    .line 103
    new-instance v15, Ljava/io/BufferedReader;

    move-object/from16 v16, v1

    .end local v1    # "endpoint":Ljava/lang/String;
    .local v16, "endpoint":Ljava/lang/String;
    new-instance v1, Ljava/io/InputStreamReader;

    move-object/from16 v17, v2

    .end local v2    # "url":Ljava/net/URL;
    .local v17, "url":Ljava/net/URL;
    invoke-virtual {v3}, Ljava/net/HttpURLConnection;->getInputStream()Ljava/io/InputStream;

    move-result-object v2

    invoke-direct {v1, v2}, Ljava/io/InputStreamReader;-><init>(Ljava/io/InputStream;)V

    invoke-direct {v15, v1}, Ljava/io/BufferedReader;-><init>(Ljava/io/Reader;)V

    move-object v1, v15

    .line 104
    .local v1, "br":Ljava/io/BufferedReader;
    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    .line 106
    .local v2, "sb":Ljava/lang/StringBuilder;
    :goto_0
    invoke-virtual {v1}, Ljava/io/BufferedReader;->readLine()Ljava/lang/String;

    move-result-object v15

    move-object/from16 v18, v15

    .local v18, "line":Ljava/lang/String;
    if-eqz v15, :cond_0

    move-object/from16 v15, v18

    .end local v18    # "line":Ljava/lang/String;
    .local v15, "line":Ljava/lang/String;
    invoke-virtual {v2, v15}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    goto :goto_0

    .line 107
    .end local v15    # "line":Ljava/lang/String;
    .restart local v18    # "line":Ljava/lang/String;
    :cond_0
    move-object/from16 v15, v18

    .end local v18    # "line":Ljava/lang/String;
    .restart local v15    # "line":Ljava/lang/String;
    invoke-virtual {v1}, Ljava/io/BufferedReader;->close()V

    .line 109
    move-object/from16 v18, v1

    .end local v1    # "br":Ljava/io/BufferedReader;
    .local v18, "br":Ljava/io/BufferedReader;
    new-instance v1, Lorg/json/JSONObject;

    move-object/from16 v19, v3

    .end local v3    # "conn":Ljava/net/HttpURLConnection;
    .local v19, "conn":Ljava/net/HttpURLConnection;
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v3

    invoke-direct {v1, v3}, Lorg/json/JSONObject;-><init>(Ljava/lang/String;)V

    .line 110
    .local v1, "res":Lorg/json/JSONObject;
    invoke-virtual {v1, v0}, Lorg/json/JSONObject;->has(Ljava/lang/String;)Z

    move-result v3

    if-eqz v3, :cond_1

    .line 111
    invoke-virtual {v1, v0}, Lorg/json/JSONObject;->getJSONObject(Ljava/lang/String;)Lorg/json/JSONObject;

    move-result-object v0

    .line 112
    .local v0, "result":Lorg/json/JSONObject;
    const-string v3, "success"

    move-object/from16 v20, v1

    .end local v1    # "res":Lorg/json/JSONObject;
    .local v20, "res":Lorg/json/JSONObject;
    const-string v1, "status"

    invoke-virtual {v0, v1}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v1

    invoke-virtual {v3, v1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1
    :try_end_7
    .catch Ljava/lang/Exception; {:try_start_7 .. :try_end_7} :catch_0

    return v1

    .line 110
    .end local v0    # "result":Lorg/json/JSONObject;
    .end local v20    # "res":Lorg/json/JSONObject;
    .restart local v1    # "res":Lorg/json/JSONObject;
    :cond_1
    move-object/from16 v20, v1

    .end local v1    # "res":Lorg/json/JSONObject;
    .restart local v20    # "res":Lorg/json/JSONObject;
    goto :goto_1

    .line 102
    .end local v15    # "line":Ljava/lang/String;
    .end local v16    # "endpoint":Ljava/lang/String;
    .end local v17    # "url":Ljava/net/URL;
    .end local v18    # "br":Ljava/io/BufferedReader;
    .end local v19    # "conn":Ljava/net/HttpURLConnection;
    .end local v20    # "res":Lorg/json/JSONObject;
    .local v1, "endpoint":Ljava/lang/String;
    .local v2, "url":Ljava/net/URL;
    .restart local v3    # "conn":Ljava/net/HttpURLConnection;
    :cond_2
    move-object/from16 v16, v1

    move-object/from16 v17, v2

    move-object/from16 v19, v3

    .line 117
    .end local v1    # "endpoint":Ljava/lang/String;
    .end local v2    # "url":Ljava/net/URL;
    .end local v3    # "conn":Ljava/net/HttpURLConnection;
    .end local v5    # "params":Lorg/json/JSONObject;
    .end local v6    # "rpc":Lorg/json/JSONObject;
    .end local v13    # "os":Ljava/io/OutputStream;
    .end local v14    # "code":I
    :goto_1
    goto :goto_9

    .line 115
    :catch_0
    move-exception v0

    goto :goto_8

    :catch_1
    move-exception v0

    goto :goto_7

    :catch_2
    move-exception v0

    goto :goto_6

    :catch_3
    move-exception v0

    goto :goto_5

    :catch_4
    move-exception v0

    goto :goto_4

    :catch_5
    move-exception v0

    goto :goto_3

    :catch_6
    move-exception v0

    goto :goto_2

    :catch_7
    move-exception v0

    move-object/from16 v4, p0

    :goto_2
    move-object/from16 v7, p1

    :goto_3
    move-object/from16 v8, p2

    :goto_4
    move/from16 v9, p3

    :goto_5
    move-object/from16 v10, p4

    :goto_6
    move/from16 v11, p5

    :goto_7
    move/from16 v12, p6

    .line 116
    .local v0, "e":Ljava/lang/Exception;
    :goto_8
    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "Error posting to Odoo: "

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v0}, Ljava/lang/Exception;->getMessage()Ljava/lang/String;

    move-result-object v2

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    const-string v2, "DiyaCRMSync"

    invoke-static {v2, v1}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    .line 118
    .end local v0    # "e":Ljava/lang/Exception;
    :goto_9
    const/4 v0, 0x0

    return v0
.end method

.method public static syncPendingCalls(Landroid/content/Context;)V
    .locals 2
    .param p0, "context"    # Landroid/content/Context;

    .line 31
    invoke-static {p0}, Lcom/diyacrm/dialer/SyncManager;->isNetworkAvailable(Landroid/content/Context;)Z

    move-result v0

    if-nez v0, :cond_0

    .line 32
    const-string v0, "DiyaCRMSync"

    const-string v1, "Offline: Keeping calls in SQLite queue."

    invoke-static {v0, v1}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    .line 33
    return-void

    .line 36
    :cond_0
    new-instance v0, Ljava/lang/Thread;

    new-instance v1, Lcom/diyacrm/dialer/SyncManager$$ExternalSyntheticLambda0;

    invoke-direct {v1, p0}, Lcom/diyacrm/dialer/SyncManager$$ExternalSyntheticLambda0;-><init>(Landroid/content/Context;)V

    invoke-direct {v0, v1}, Ljava/lang/Thread;-><init>(Ljava/lang/Runnable;)V

    .line 69
    invoke-virtual {v0}, Ljava/lang/Thread;->start()V

    .line 70
    return-void
.end method

.method public static fetchRecentCallsFromDevice(Landroid/content/Context;Landroid/content/SharedPreferences;Lcom/diyacrm/dialer/OfflineDbHelper;)V
    .locals 21
    .param p0, "context"    # Landroid/content/Context;
    .param p1, "prefs"    # Landroid/content/SharedPreferences;
    .param p2, "db"    # Lcom/diyacrm/dialer/OfflineDbHelper;

    const-string v0, "DiyaCRMSync"

    :try_start_0
    invoke-virtual/range {p0 .. p0}, Landroid/content/Context;->getContentResolver()Landroid/content/ContentResolver;

    move-result-object v1

    sget-object v2, Landroid/provider/CallLog$Calls;->CONTENT_URI:Landroid/net/Uri;

    const/4 v3, 0x0

    const/4 v4, 0x0

    const/4 v5, 0x0

    const-string v6, "date DESC LIMIT 30"

    invoke-virtual/range {v1 .. v6}, Landroid/content/ContentResolver;->query(Landroid/net/Uri;[Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;)Landroid/database/Cursor;

    move-result-object v1

    if-eqz v1, :cond_6

    invoke-interface {v1}, Landroid/database/Cursor;->moveToFirst()Z

    move-result v2

    if-eqz v2, :cond_5

    const-string v2, "user_id"

    const/4 v3, 0x0

    move-object/from16 v4, p1

    invoke-interface {v4, v2, v3}, Landroid/content/SharedPreferences;->getInt(Ljava/lang/String;I)I

    move-result v2

    const-string v5, "company_id"

    invoke-interface {v4, v5, v3}, Landroid/content/SharedPreferences;->getInt(Ljava/lang/String;I)I

    move-result v3

    new-instance v4, Ljava/text/SimpleDateFormat;

    const-string v5, "yyyy-MM-dd HH:mm:ss"

    invoke-static {}, Ljava/util/Locale;->getDefault()Ljava/util/Locale;

    move-result-object v6

    invoke-direct {v4, v5, v6}, Ljava/text/SimpleDateFormat;-><init>(Ljava/lang/String;Ljava/util/Locale;)V

    :cond_0
    const-string v5, "_id"

    invoke-interface {v1, v5}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v5

    invoke-interface {v1, v5}, Landroid/database/Cursor;->getString(I)Ljava/lang/String;

    move-result-object v5

    const-string v6, "number"

    invoke-interface {v1, v6}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v6

    invoke-interface {v1, v6}, Landroid/database/Cursor;->getString(I)Ljava/lang/String;

    move-result-object v6

    const-string v7, "type"

    invoke-interface {v1, v7}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v7

    invoke-interface {v1, v7}, Landroid/database/Cursor;->getInt(I)I

    move-result v7

    const-string v8, "duration"

    invoke-interface {v1, v8}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v8

    invoke-interface {v1, v8}, Landroid/database/Cursor;->getInt(I)I

    move-result v8

    const-string v9, "date"

    invoke-interface {v1, v9}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v9

    invoke-interface {v1, v9}, Landroid/database/Cursor;->getLong(I)J

    move-result-wide v9

    new-instance v11, Ljava/util/Date;

    invoke-direct {v11, v9, v10}, Ljava/util/Date;-><init>(J)V

    invoke-virtual {v4, v11}, Ljava/text/SimpleDateFormat;->format(Ljava/util/Date;)Ljava/lang/String;

    move-result-object v11

    const-string v12, "incoming_answered"

    const/4 v13, 0x2

    if-ne v7, v13, :cond_1

    if-lez v8, :cond_ff_noans

    const-string v12, "outgoing_answered"

    goto :goto_type_done

    :cond_ff_noans
    const-string v12, "outgoing_no_answer"

    goto :goto_type_done

    :cond_1
    const/4 v13, 0x3

    if-ne v7, v13, :cond_2

    const-string v12, "incoming_missed"

    goto :goto_type_done

    :cond_2
    const/4 v13, 0x5

    if-ne v7, v13, :cond_3

    const-string v12, "incoming_rejected"

    :cond_3
    :goto_type_done
    move-object/from16 v7, p0

    invoke-static {v7, v1}, Lcom/diyacrm/dialer/SimFilter;->shouldRecordCall(Landroid/content/Context;Landroid/database/Cursor;)Z

    move-result v13

    if-eqz v13, :cond_4

    move-object/from16 v13, p2

    move-object v14, v5

    move-object v15, v6

    move-object/from16 v16, v12

    move/from16 v17, v8

    move-object/from16 v18, v11

    move/from16 v19, v2

    move/from16 v20, v3

    invoke-virtual/range {v13 .. v20}, Lcom/diyacrm/dialer/OfflineDbHelper;->insertCall(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;ILjava/lang/String;II)Z

    invoke-static {v7, v6, v9, v10}, Lcom/diyacrm/dialer/RecordingFinder;->findRecordingForCall(Landroid/content/Context;Ljava/lang/String;J)Ljava/lang/String;

    move-result-object v6

    if-eqz v6, :cond_4

    invoke-static {v7, v6, v5}, Lcom/diyacrm/dialer/UploadManager;->uploadFileAsync(Landroid/content/Context;Ljava/lang/String;Ljava/lang/String;)V

    :cond_4
    invoke-interface {v1}, Landroid/database/Cursor;->moveToNext()Z

    move-result v5

    if-nez v5, :cond_0

    :cond_5
    invoke-interface {v1}, Landroid/database/Cursor;->close()V
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    goto :goto_ret

    :catch_0
    move-exception v1

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "Error fetching recent calls: "

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v1}, Ljava/lang/Exception;->getMessage()Ljava/lang/String;

    move-result-object v1

    invoke-virtual {v2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-static {v0, v1}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    :cond_6
    :goto_ret
    return-void
.end method

