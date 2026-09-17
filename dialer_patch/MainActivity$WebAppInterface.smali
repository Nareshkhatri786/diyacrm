.class public Lcom/diyacrm/dialer/MainActivity$WebAppInterface;
.super Ljava/lang/Object;
.source "MainActivity.java"


# annotations
.annotation system Ldalvik/annotation/EnclosingClass;
    value = Lcom/diyacrm/dialer/MainActivity;
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x1
    name = "WebAppInterface"
.end annotation


# instance fields
.field mContext:Landroid/content/Context;

.field final synthetic this$0:Lcom/diyacrm/dialer/MainActivity;


# direct methods
.method public static synthetic $r8$lambda$0nbdawXjLdifzyxwK__ZtqJldS4(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;)V
    .locals 0

    invoke-direct {p0}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->lambda$logout$1()V

    return-void
.end method

.method public static synthetic $r8$lambda$93VFO4ZB1QrkHmiF82S-7yIUIBE(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;)V
    .locals 0

    invoke-direct {p0}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->lambda$login$4()V

    return-void
.end method

.method public static synthetic $r8$lambda$AbrRoEABFgZL-PbB1XzGS6tmFz4(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;Ljava/lang/String;)V
    .locals 0

    invoke-direct {p0, p1}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->lambda$login$3(Ljava/lang/String;)V

    return-void
.end method

.method public static synthetic $r8$lambda$H2h60MN6WEYhJOfXye3eXSqIkt0(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V
    .locals 0

    invoke-direct {p0, p1, p2, p3}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->lambda$login$6(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V

    return-void
.end method

.method public static synthetic $r8$lambda$IKNRhiePcUYIgjNMJEFVR2Uh3Po(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;)V
    .locals 0

    invoke-direct {p0}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->lambda$syncNow$0()V

    return-void
.end method

.method public static synthetic $r8$lambda$WioW6w5GV_MUly_KNW4ECH7U3Eo(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;Lorg/json/JSONObject;)V
    .locals 0

    invoke-direct {p0, p1}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->lambda$login$2(Lorg/json/JSONObject;)V

    return-void
.end method

.method public static synthetic $r8$lambda$sQzsyAtcvwSAH-cPQt-Mwkhd7Ac(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;Ljava/lang/Exception;)V
    .locals 0

    invoke-direct {p0, p1}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->lambda$login$5(Ljava/lang/Exception;)V

    return-void
.end method

.method constructor <init>(Lcom/diyacrm/dialer/MainActivity;Landroid/content/Context;)V
    .locals 0
    .param p1, "this$0"    # Lcom/diyacrm/dialer/MainActivity;
    .param p2, "c"    # Landroid/content/Context;

    .line 98
    iput-object p1, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->this$0:Lcom/diyacrm/dialer/MainActivity;

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    .line 99
    iput-object p2, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    .line 100
    return-void
.end method

.method private synthetic lambda$login$2(Lorg/json/JSONObject;)V
    .locals 3
    .param p1, "result"    # Lorg/json/JSONObject;

    .line 206
    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "Welcome, "

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v2, "user_name"

    invoke-virtual {p1, v2}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v2

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    const/4 v2, 0x0

    invoke-static {v0, v1, v2}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;

    move-result-object v0

    invoke-virtual {v0}, Landroid/widget/Toast;->show()V

    .line 207
    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->this$0:Lcom/diyacrm/dialer/MainActivity;

    invoke-static {v0}, Lcom/diyacrm/dialer/MainActivity;->-$$Nest$mrefreshUI(Lcom/diyacrm/dialer/MainActivity;)V

    .line 208
    return-void
.end method

.method private synthetic lambda$login$3(Ljava/lang/String;)V
    .locals 2
    .param p1, "msg"    # Ljava/lang/String;

    .line 212
    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    const/4 v1, 0x1

    invoke-static {v0, p1, v1}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;

    move-result-object v0

    invoke-virtual {v0}, Landroid/widget/Toast;->show()V

    return-void
.end method

.method private synthetic lambda$login$4()V
    .locals 3

    .line 217
    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    const-string v1, "Could not connect to CRM server."

    const/4 v2, 0x0

    invoke-static {v0, v1, v2}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;

    move-result-object v0

    invoke-virtual {v0}, Landroid/widget/Toast;->show()V

    return-void
.end method

.method private synthetic lambda$login$5(Ljava/lang/Exception;)V
    .locals 3
    .param p1, "e"    # Ljava/lang/Exception;

    .line 219
    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "Login Error: "

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {p1}, Ljava/lang/Exception;->getMessage()Ljava/lang/String;

    move-result-object v2

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    const/4 v2, 0x1

    invoke-static {v0, v1, v2}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;

    move-result-object v0

    invoke-virtual {v0}, Landroid/widget/Toast;->show()V

    return-void
.end method

.method private synthetic lambda$login$6(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V
    .locals 22
    .param p1, "serverUrl"    # Ljava/lang/String;
    .param p2, "username"    # Ljava/lang/String;
    .param p3, "password"    # Ljava/lang/String;

    .line 161
    move-object/from16 v1, p0

    move-object/from16 v2, p1

    const-string v0, "company_name"

    const-string v3, "company_id"

    const-string v4, "user_name"

    const-string v5, "user_id"

    const-string v6, "result"

    :try_start_0
    new-instance v7, Ljava/lang/StringBuilder;

    invoke-direct {v7}, Ljava/lang/StringBuilder;-><init>()V

    const-string v8, "/+$"

    const-string v9, ""

    invoke-virtual {v2, v8, v9}, Ljava/lang/String;->replaceAll(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v8

    invoke-virtual {v7, v8}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v7

    const-string v8, "/api/call_tracker/login"

    invoke-virtual {v7, v8}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v7

    invoke-virtual {v7}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v7

    .line 162
    .local v7, "endpoint":Ljava/lang/String;
    new-instance v8, Ljava/net/URL;

    invoke-direct {v8, v7}, Ljava/net/URL;-><init>(Ljava/lang/String;)V

    .line 163
    .local v8, "url":Ljava/net/URL;
    invoke-virtual {v8}, Ljava/net/URL;->openConnection()Ljava/net/URLConnection;

    move-result-object v9

    check-cast v9, Ljava/net/HttpURLConnection;

    .line 164
    .local v9, "conn":Ljava/net/HttpURLConnection;
    const-string v10, "POST"

    invoke-virtual {v9, v10}, Ljava/net/HttpURLConnection;->setRequestMethod(Ljava/lang/String;)V

    .line 165
    const-string v10, "Content-Type"

    const-string v11, "application/json"

    invoke-virtual {v9, v10, v11}, Ljava/net/HttpURLConnection;->setRequestProperty(Ljava/lang/String;Ljava/lang/String;)V

    .line 166
    const/16 v10, 0x1f40

    invoke-virtual {v9, v10}, Ljava/net/HttpURLConnection;->setConnectTimeout(I)V

    .line 167
    invoke-virtual {v9, v10}, Ljava/net/HttpURLConnection;->setReadTimeout(I)V

    .line 168
    const/4 v10, 0x1

    invoke-virtual {v9, v10}, Ljava/net/HttpURLConnection;->setDoOutput(Z)V

    .line 170
    new-instance v11, Lorg/json/JSONObject;

    invoke-direct {v11}, Lorg/json/JSONObject;-><init>()V

    .line 171
    .local v11, "params":Lorg/json/JSONObject;
    const-string v12, "login"
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_2

    move-object/from16 v13, p2

    :try_start_1
    invoke-virtual {v11, v12, v13}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    .line 172
    const-string v12, "password"
    :try_end_1
    .catch Ljava/lang/Exception; {:try_start_1 .. :try_end_1} :catch_1

    move-object/from16 v14, p3

    :try_start_2
    invoke-virtual {v11, v12, v14}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    .line 174
    new-instance v12, Lorg/json/JSONObject;

    invoke-direct {v12}, Lorg/json/JSONObject;-><init>()V

    .line 175
    .local v12, "rpc":Lorg/json/JSONObject;
    const-string v15, "jsonrpc"

    const-string v10, "2.0"

    invoke-virtual {v12, v15, v10}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    .line 176
    const-string v10, "method"

    const-string v15, "call"

    invoke-virtual {v12, v10, v15}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    .line 177
    const-string v10, "params"

    invoke-virtual {v12, v10, v11}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    .line 178
    const-string v10, "id"

    const/4 v15, 0x1

    invoke-virtual {v12, v10, v15}, Lorg/json/JSONObject;->put(Ljava/lang/String;I)Lorg/json/JSONObject;

    .line 180
    invoke-virtual {v9}, Ljava/net/HttpURLConnection;->getOutputStream()Ljava/io/OutputStream;

    move-result-object v10

    .line 181
    .local v10, "os":Ljava/io/OutputStream;
    invoke-virtual {v12}, Lorg/json/JSONObject;->toString()Ljava/lang/String;

    move-result-object v15

    move-object/from16 v16, v7

    .end local v7    # "endpoint":Ljava/lang/String;
    .local v16, "endpoint":Ljava/lang/String;
    const-string v7, "UTF-8"

    invoke-virtual {v15, v7}, Ljava/lang/String;->getBytes(Ljava/lang/String;)[B

    move-result-object v7

    invoke-virtual {v10, v7}, Ljava/io/OutputStream;->write([B)V

    .line 182
    invoke-virtual {v10}, Ljava/io/OutputStream;->close()V

    .line 184
    invoke-virtual {v9}, Ljava/net/HttpURLConnection;->getResponseCode()I

    move-result v7

    const/16 v15, 0xc8

    if-ne v7, v15, :cond_3

    .line 185
    new-instance v7, Ljava/io/BufferedReader;

    new-instance v15, Ljava/io/InputStreamReader;

    move-object/from16 v17, v8

    .end local v8    # "url":Ljava/net/URL;
    .local v17, "url":Ljava/net/URL;
    invoke-virtual {v9}, Ljava/net/HttpURLConnection;->getInputStream()Ljava/io/InputStream;

    move-result-object v8

    invoke-direct {v15, v8}, Ljava/io/InputStreamReader;-><init>(Ljava/io/InputStream;)V

    invoke-direct {v7, v15}, Ljava/io/BufferedReader;-><init>(Ljava/io/Reader;)V

    .line 186
    .local v7, "br":Ljava/io/BufferedReader;
    new-instance v8, Ljava/lang/StringBuilder;

    invoke-direct {v8}, Ljava/lang/StringBuilder;-><init>()V

    .line 188
    .local v8, "sb":Ljava/lang/StringBuilder;
    :goto_0
    invoke-virtual {v7}, Ljava/io/BufferedReader;->readLine()Ljava/lang/String;

    move-result-object v15

    move-object/from16 v18, v15

    .local v18, "line":Ljava/lang/String;
    if-eqz v15, :cond_0

    move-object/from16 v15, v18

    .end local v18    # "line":Ljava/lang/String;
    .local v15, "line":Ljava/lang/String;
    invoke-virtual {v8, v15}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    goto :goto_0

    .line 189
    .end local v15    # "line":Ljava/lang/String;
    .restart local v18    # "line":Ljava/lang/String;
    :cond_0
    move-object/from16 v15, v18

    .end local v18    # "line":Ljava/lang/String;
    .restart local v15    # "line":Ljava/lang/String;
    invoke-virtual {v7}, Ljava/io/BufferedReader;->close()V

    .line 191
    move-object/from16 v18, v7

    .end local v7    # "br":Ljava/io/BufferedReader;
    .local v18, "br":Ljava/io/BufferedReader;
    new-instance v7, Lorg/json/JSONObject;

    move-object/from16 v19, v9

    .end local v9    # "conn":Ljava/net/HttpURLConnection;
    .local v19, "conn":Ljava/net/HttpURLConnection;
    invoke-virtual {v8}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v9

    invoke-direct {v7, v9}, Lorg/json/JSONObject;-><init>(Ljava/lang/String;)V

    .line 192
    .local v7, "res":Lorg/json/JSONObject;
    invoke-virtual {v7, v6}, Lorg/json/JSONObject;->has(Ljava/lang/String;)Z

    move-result v9

    if-eqz v9, :cond_2

    .line 193
    invoke-virtual {v7, v6}, Lorg/json/JSONObject;->getJSONObject(Ljava/lang/String;)Lorg/json/JSONObject;

    move-result-object v6

    .line 194
    .local v6, "result":Lorg/json/JSONObject;
    const-string v9, "success"

    move-object/from16 v20, v7

    .end local v7    # "res":Lorg/json/JSONObject;
    .local v20, "res":Lorg/json/JSONObject;
    const-string v7, "status"

    invoke-virtual {v6, v7}, Lorg/json/JSONObject;->optString(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v7

    invoke-virtual {v9, v7}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v7

    if-eqz v7, :cond_1

    .line 195
    iget-object v7, v1, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    const-string v9, "DiyaCRM_Prefs"

    move-object/from16 v21, v8

    .end local v8    # "sb":Ljava/lang/StringBuilder;
    .local v21, "sb":Ljava/lang/StringBuilder;
    const/4 v8, 0x0

    invoke-virtual {v7, v9, v8}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v7

    .line 196
    .local v7, "prefs":Landroid/content/SharedPreferences;
    invoke-interface {v7}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;

    move-result-object v8

    const-string v9, "server_url"

    .line 197
    invoke-interface {v8, v9, v2}, Landroid/content/SharedPreferences$Editor;->putString(Ljava/lang/String;Ljava/lang/String;)Landroid/content/SharedPreferences$Editor;

    move-result-object v8

    .line 198
    invoke-virtual {v6, v5}, Lorg/json/JSONObject;->getInt(Ljava/lang/String;)I

    move-result v9

    invoke-interface {v8, v5, v9}, Landroid/content/SharedPreferences$Editor;->putInt(Ljava/lang/String;I)Landroid/content/SharedPreferences$Editor;

    move-result-object v5

    .line 199
    invoke-virtual {v6, v4}, Lorg/json/JSONObject;->getString(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v8

    invoke-interface {v5, v4, v8}, Landroid/content/SharedPreferences$Editor;->putString(Ljava/lang/String;Ljava/lang/String;)Landroid/content/SharedPreferences$Editor;

    move-result-object v4

    .line 200
    invoke-virtual {v6, v3}, Lorg/json/JSONObject;->getInt(Ljava/lang/String;)I

    move-result v5

    invoke-interface {v4, v3, v5}, Landroid/content/SharedPreferences$Editor;->putInt(Ljava/lang/String;I)Landroid/content/SharedPreferences$Editor;

    move-result-object v3

    .line 201
    invoke-virtual {v6, v0}, Lorg/json/JSONObject;->getString(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v4

    invoke-interface {v3, v0, v4}, Landroid/content/SharedPreferences$Editor;->putString(Ljava/lang/String;Ljava/lang/String;)Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    const-string v3, "install_timestamp"

    .line 202
    invoke-static {}, Ljava/lang/System;->currentTimeMillis()J

    move-result-wide v4

    invoke-interface {v0, v3, v4, v5}, Landroid/content/SharedPreferences$Editor;->putLong(Ljava/lang/String;J)Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    .line 203
    invoke-interface {v0}, Landroid/content/SharedPreferences$Editor;->apply()V

    .line 205
    iget-object v0, v1, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->this$0:Lcom/diyacrm/dialer/MainActivity;

    new-instance v3, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda2;

    invoke-direct {v3, v1, v6}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda2;-><init>(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;Lorg/json/JSONObject;)V

    invoke-virtual {v0, v3}, Lcom/diyacrm/dialer/MainActivity;->runOnUiThread(Ljava/lang/Runnable;)V

    .line 209
    return-void

    .line 211
    .end local v7    # "prefs":Landroid/content/SharedPreferences;
    .end local v21    # "sb":Ljava/lang/StringBuilder;
    .restart local v8    # "sb":Ljava/lang/StringBuilder;
    :cond_1
    move-object/from16 v21, v8

    .end local v8    # "sb":Ljava/lang/StringBuilder;
    .restart local v21    # "sb":Ljava/lang/StringBuilder;
    const-string v0, "message"

    const-string v3, "Login failed"

    invoke-virtual {v6, v0, v3}, Lorg/json/JSONObject;->optString(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v0

    .line 212
    .local v0, "msg":Ljava/lang/String;
    iget-object v3, v1, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->this$0:Lcom/diyacrm/dialer/MainActivity;

    new-instance v4, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda3;

    invoke-direct {v4, v1, v0}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda3;-><init>(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;Ljava/lang/String;)V

    invoke-virtual {v3, v4}, Lcom/diyacrm/dialer/MainActivity;->runOnUiThread(Ljava/lang/Runnable;)V

    .line 213
    return-void

    .line 192
    .end local v0    # "msg":Ljava/lang/String;
    .end local v6    # "result":Lorg/json/JSONObject;
    .end local v20    # "res":Lorg/json/JSONObject;
    .end local v21    # "sb":Ljava/lang/StringBuilder;
    .local v7, "res":Lorg/json/JSONObject;
    .restart local v8    # "sb":Ljava/lang/StringBuilder;
    :cond_2
    move-object/from16 v20, v7

    move-object/from16 v21, v8

    .end local v7    # "res":Lorg/json/JSONObject;
    .end local v8    # "sb":Ljava/lang/StringBuilder;
    .restart local v20    # "res":Lorg/json/JSONObject;
    .restart local v21    # "sb":Ljava/lang/StringBuilder;
    goto :goto_1

    .line 184
    .end local v15    # "line":Ljava/lang/String;
    .end local v17    # "url":Ljava/net/URL;
    .end local v18    # "br":Ljava/io/BufferedReader;
    .end local v19    # "conn":Ljava/net/HttpURLConnection;
    .end local v20    # "res":Lorg/json/JSONObject;
    .end local v21    # "sb":Ljava/lang/StringBuilder;
    .local v8, "url":Ljava/net/URL;
    .restart local v9    # "conn":Ljava/net/HttpURLConnection;
    :cond_3
    move-object/from16 v17, v8

    move-object/from16 v19, v9

    .line 217
    .end local v8    # "url":Ljava/net/URL;
    .end local v9    # "conn":Ljava/net/HttpURLConnection;
    .restart local v17    # "url":Ljava/net/URL;
    .restart local v19    # "conn":Ljava/net/HttpURLConnection;
    :goto_1
    iget-object v0, v1, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->this$0:Lcom/diyacrm/dialer/MainActivity;

    new-instance v3, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda4;

    invoke-direct {v3, v1}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda4;-><init>(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;)V

    invoke-virtual {v0, v3}, Lcom/diyacrm/dialer/MainActivity;->runOnUiThread(Ljava/lang/Runnable;)V
    :try_end_2
    .catch Ljava/lang/Exception; {:try_start_2 .. :try_end_2} :catch_0

    .line 220
    .end local v10    # "os":Ljava/io/OutputStream;
    .end local v11    # "params":Lorg/json/JSONObject;
    .end local v12    # "rpc":Lorg/json/JSONObject;
    .end local v16    # "endpoint":Ljava/lang/String;
    .end local v17    # "url":Ljava/net/URL;
    .end local v19    # "conn":Ljava/net/HttpURLConnection;
    goto :goto_4

    .line 218
    :catch_0
    move-exception v0

    goto :goto_3

    :catch_1
    move-exception v0

    goto :goto_2

    :catch_2
    move-exception v0

    move-object/from16 v13, p2

    :goto_2
    move-object/from16 v14, p3

    .line 219
    .local v0, "e":Ljava/lang/Exception;
    :goto_3
    iget-object v3, v1, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->this$0:Lcom/diyacrm/dialer/MainActivity;

    new-instance v4, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda5;

    invoke-direct {v4, v1, v0}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda5;-><init>(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;Ljava/lang/Exception;)V

    invoke-virtual {v3, v4}, Lcom/diyacrm/dialer/MainActivity;->runOnUiThread(Ljava/lang/Runnable;)V

    .line 221
    .end local v0    # "e":Ljava/lang/Exception;
    :goto_4
    return-void
.end method

.method private synthetic lambda$logout$1()V
    .locals 1

    .line 154
    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->this$0:Lcom/diyacrm/dialer/MainActivity;

    invoke-static {v0}, Lcom/diyacrm/dialer/MainActivity;->-$$Nest$mrefreshUI(Lcom/diyacrm/dialer/MainActivity;)V

    return-void
.end method

.method private synthetic lambda$syncNow$0()V
    .locals 3

    .line 141
    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    const-string v1, "Syncing calls to Odoo..."

    const/4 v2, 0x0

    invoke-static {v0, v1, v2}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;

    move-result-object v0

    invoke-virtual {v0}, Landroid/widget/Toast;->show()V

    return-void
.end method


# virtual methods
.method public getAuthInfo()Ljava/lang/String;
    .locals 8
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    .line 104
    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    const-string v1, "DiyaCRM_Prefs"

    const/4 v2, 0x0

    invoke-virtual {v0, v1, v2}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    .line 105
    .local v0, "prefs":Landroid/content/SharedPreferences;
    const-string v1, "user_id"

    invoke-interface {v0, v1, v2}, Landroid/content/SharedPreferences;->getInt(Ljava/lang/String;I)I

    move-result v1

    if-lez v1, :cond_0

    const/4 v2, 0x1

    :cond_0
    move v1, v2

    .line 106
    .local v1, "isLoggedIn":Z
    const-string v2, "user_name"

    const-string v3, ""

    invoke-interface {v0, v2, v3}, Landroid/content/SharedPreferences;->getString(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v2

    .line 107
    .local v2, "name":Ljava/lang/String;
    const-string v4, "company_name"

    invoke-interface {v0, v4, v3}, Landroid/content/SharedPreferences;->getString(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v3

    .line 108
    .local v3, "comp":Ljava/lang/String;
    new-instance v4, Lcom/diyacrm/dialer/OfflineDbHelper;

    iget-object v5, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    invoke-direct {v4, v5}, Lcom/diyacrm/dialer/OfflineDbHelper;-><init>(Landroid/content/Context;)V

    .line 109
    .local v4, "db":Lcom/diyacrm/dialer/OfflineDbHelper;
    invoke-virtual {v4}, Lcom/diyacrm/dialer/OfflineDbHelper;->getUnsyncedCount()I

    move-result v5

    .line 111
    .local v5, "unsynced":I
    new-instance v6, Lorg/json/JSONObject;

    invoke-direct {v6}, Lorg/json/JSONObject;-><init>()V

    .line 113
    .local v6, "obj":Lorg/json/JSONObject;
    :try_start_0
    const-string v7, "isLoggedIn"

    invoke-virtual {v6, v7, v1}, Lorg/json/JSONObject;->put(Ljava/lang/String;Z)Lorg/json/JSONObject;

    .line 114
    const-string v7, "userName"

    invoke-virtual {v6, v7, v2}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    .line 115
    const-string v7, "companyName"

    invoke-virtual {v6, v7, v3}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    .line 116
    const-string v7, "unsynced"

    invoke-virtual {v6, v7, v5}, Lorg/json/JSONObject;->put(Ljava/lang/String;I)Lorg/json/JSONObject;
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    goto :goto_0

    .line 117
    :catch_0
    move-exception v7

    :goto_0
    nop

    .line 118
    invoke-virtual {v6}, Lorg/json/JSONObject;->toString()Ljava/lang/String;

    move-result-object v7

    return-object v7
.end method

.method public getRecentLogs()Ljava/lang/String;
    .locals 2
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    .line 146
    new-instance v0, Lcom/diyacrm/dialer/OfflineDbHelper;

    iget-object v1, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    invoke-direct {v0, v1}, Lcom/diyacrm/dialer/OfflineDbHelper;-><init>(Landroid/content/Context;)V

    .line 147
    .local v0, "db":Lcom/diyacrm/dialer/OfflineDbHelper;
    invoke-virtual {v0}, Lcom/diyacrm/dialer/OfflineDbHelper;->getRecentCallsJson()Lorg/json/JSONArray;

    move-result-object v1

    invoke-virtual {v1}, Lorg/json/JSONArray;->toString()Ljava/lang/String;

    move-result-object v1

    return-object v1
.end method

.method public login(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V
    .locals 2
    .param p1, "serverUrl"    # Ljava/lang/String;
    .param p2, "username"    # Ljava/lang/String;
    .param p3, "password"    # Ljava/lang/String;
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    .line 159
    new-instance v0, Ljava/lang/Thread;

    new-instance v1, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda0;

    invoke-direct {v1, p0, p1, p2, p3}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda0;-><init>(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V

    invoke-direct {v0, v1}, Ljava/lang/Thread;-><init>(Ljava/lang/Runnable;)V

    .line 221
    invoke-virtual {v0}, Ljava/lang/Thread;->start()V

    .line 222
    return-void
.end method

.method public logout()V
    .locals 3
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    .line 152
    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    const-string v1, "DiyaCRM_Prefs"

    const/4 v2, 0x0

    invoke-virtual {v0, v1, v2}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    .line 153
    .local v0, "prefs":Landroid/content/SharedPreferences;
    invoke-interface {v0}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;

    move-result-object v1

    invoke-interface {v1}, Landroid/content/SharedPreferences$Editor;->clear()Landroid/content/SharedPreferences$Editor;

    move-result-object v1

    invoke-interface {v1}, Landroid/content/SharedPreferences$Editor;->apply()V

    .line 154
    iget-object v1, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->this$0:Lcom/diyacrm/dialer/MainActivity;

    new-instance v2, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda1;

    invoke-direct {v2, p0}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda1;-><init>(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;)V

    invoke-virtual {v1, v2}, Lcom/diyacrm/dialer/MainActivity;->runOnUiThread(Ljava/lang/Runnable;)V

    .line 155
    return-void
.end method

.method public makePhoneCall(Ljava/lang/String;)V
    .locals 5
    .param p1, "phoneNumber"    # Ljava/lang/String;
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    .line 124
    const-string v0, "android.intent.action.DIAL"

    const-string v1, "tel:"

    :try_start_0
    new-instance v2, Landroid/content/Intent;

    const-string v3, "android.intent.action.CALL"

    invoke-direct {v2, v3}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    .line 125
    .local v2, "callIntent":Landroid/content/Intent;
    new-instance v3, Ljava/lang/StringBuilder;

    invoke-direct {v3}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v3, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v3

    invoke-virtual {v3, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v3

    invoke-virtual {v3}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v3

    invoke-static {v3}, Landroid/net/Uri;->parse(Ljava/lang/String;)Landroid/net/Uri;

    move-result-object v3

    invoke-virtual {v2, v3}, Landroid/content/Intent;->setData(Landroid/net/Uri;)Landroid/content/Intent;

    .line 126
    iget-object v3, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    const-string v4, "android.permission.CALL_PHONE"

    invoke-static {v3, v4}, Landroidx/core/app/ActivityCompat;->checkSelfPermission(Landroid/content/Context;Ljava/lang/String;)I

    move-result v3

    if-nez v3, :cond_0

    .line 127
    iget-object v3, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    invoke-virtual {v3, v2}, Landroid/content/Context;->startActivity(Landroid/content/Intent;)V

    goto :goto_0

    .line 129
    :cond_0
    new-instance v3, Landroid/content/Intent;

    new-instance v4, Ljava/lang/StringBuilder;

    invoke-direct {v4}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v4, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v4

    invoke-virtual {v4, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v4

    invoke-virtual {v4}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v4

    invoke-static {v4}, Landroid/net/Uri;->parse(Ljava/lang/String;)Landroid/net/Uri;

    move-result-object v4

    invoke-direct {v3, v0, v4}, Landroid/content/Intent;-><init>(Ljava/lang/String;Landroid/net/Uri;)V

    .line 130
    .local v3, "dialIntent":Landroid/content/Intent;
    iget-object v4, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    invoke-virtual {v4, v3}, Landroid/content/Context;->startActivity(Landroid/content/Intent;)V
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    .line 135
    .end local v2    # "callIntent":Landroid/content/Intent;
    .end local v3    # "dialIntent":Landroid/content/Intent;
    :goto_0
    goto :goto_1

    .line 132
    :catch_0
    move-exception v2

    .line 133
    .local v2, "e":Ljava/lang/Exception;
    new-instance v3, Landroid/content/Intent;

    new-instance v4, Ljava/lang/StringBuilder;

    invoke-direct {v4}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v4, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-static {v1}, Landroid/net/Uri;->parse(Ljava/lang/String;)Landroid/net/Uri;

    move-result-object v1

    invoke-direct {v3, v0, v1}, Landroid/content/Intent;-><init>(Ljava/lang/String;Landroid/net/Uri;)V

    move-object v0, v3

    .line 134
    .local v0, "dialIntent":Landroid/content/Intent;
    iget-object v1, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    invoke-virtual {v1, v0}, Landroid/content/Context;->startActivity(Landroid/content/Intent;)V

    .line 136
    .end local v0    # "dialIntent":Landroid/content/Intent;
    .end local v2    # "e":Ljava/lang/Exception;
    :goto_1
    return-void
.end method

.method public syncNow()V
    .locals 2
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    .line 140
    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    invoke-static {v0}, Lcom/diyacrm/dialer/SyncManager;->syncPendingCalls(Landroid/content/Context;)V

    .line 141
    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->this$0:Lcom/diyacrm/dialer/MainActivity;

    new-instance v1, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda6;

    invoke-direct {v1, p0}, Lcom/diyacrm/dialer/MainActivity$WebAppInterface$$ExternalSyntheticLambda6;-><init>(Lcom/diyacrm/dialer/MainActivity$WebAppInterface;)V

    invoke-virtual {v0, v1}, Lcom/diyacrm/dialer/MainActivity;->runOnUiThread(Ljava/lang/Runnable;)V

    .line 142
    return-void
.end method

# ===== DiyaCRM: SIM Selection Bridge Methods =====

.method public getTrackedSim()I
    .locals 1

    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    invoke-static {v0}, Lcom/diyacrm/dialer/SimFilter;->getTrackedSim(Landroid/content/Context;)I

    move-result v0

    return v0
.end method

.method public setTrackedSim(I)V
    .locals 1

    iget-object v0, p0, Lcom/diyacrm/dialer/MainActivity$WebAppInterface;->mContext:Landroid/content/Context;

    invoke-static {v0, p1}, Lcom/diyacrm/dialer/SimFilter;->setTrackedSim(Landroid/content/Context;I)V

    return-void
.end method

# ===== End SIM Selection Bridge Methods =====

