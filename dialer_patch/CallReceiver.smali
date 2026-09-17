.class public Lcom/diyacrm/dialer/CallReceiver;
.super Landroid/content/BroadcastReceiver;
.source "CallReceiver.java"


# static fields
.field private static final TAG:Ljava/lang/String; = "DiyaCRMCallReceiver"

.field private static isIncoming:Z

.field private static lastState:I


# direct methods
.method public static synthetic $r8$lambda$QkxIGn9FERHGdRDtYlibI9l5VVI(Lcom/diyacrm/dialer/CallReceiver;Landroid/content/Context;)V
    .locals 0

    invoke-direct {p0, p1}, Lcom/diyacrm/dialer/CallReceiver;->lambda$onCallStateChanged$0(Landroid/content/Context;)V

    return-void
.end method

.method static constructor <clinit>()V
    .locals 1

    .line 19
    const/4 v0, 0x0

    sput v0, Lcom/diyacrm/dialer/CallReceiver;->lastState:I

    .line 20
    sput-boolean v0, Lcom/diyacrm/dialer/CallReceiver;->isIncoming:Z

    return-void
.end method

.method public constructor <init>()V
    .locals 0

    .line 17
    invoke-direct {p0}, Landroid/content/BroadcastReceiver;-><init>()V

    return-void
.end method

.method private fetchLatestCallLog(Landroid/content/Context;)V
    .locals 21
    .param p1, "context"    # Landroid/content/Context;

    .line 67
    move-object/from16 v1, p1

    const-string v0, "install_timestamp"

    const-string v2, "DiyaCRMCallReceiver"

    :try_start_0
    const-string v3, "DiyaCRM_Prefs"

    const/4 v4, 0x0

    invoke-virtual {v1, v3, v4}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v3

    .line 68
    .local v3, "prefs":Landroid/content/SharedPreferences;
    const-wide/16 v5, 0x0

    invoke-interface {v3, v0, v5, v6}, Landroid/content/SharedPreferences;->getLong(Ljava/lang/String;J)J

    move-result-wide v7

    .line 69
    .local v7, "installTime":J
    cmp-long v5, v7, v5

    if-nez v5, :cond_0

    .line 70
    invoke-static {}, Ljava/lang/System;->currentTimeMillis()J

    move-result-wide v5

    move-wide v7, v5

    .line 71
    invoke-interface {v3}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;

    move-result-object v5

    invoke-interface {v5, v0, v7, v8}, Landroid/content/SharedPreferences$Editor;->putLong(Ljava/lang/String;J)Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    invoke-interface {v0}, Landroid/content/SharedPreferences$Editor;->apply()V

    .line 74
    :cond_0
    const-string v0, "user_id"

    invoke-interface {v3, v0, v4}, Landroid/content/SharedPreferences;->getInt(Ljava/lang/String;I)I

    move-result v15

    .line 75
    .local v15, "userId":I
    const-string v0, "company_id"

    invoke-interface {v3, v0, v4}, Landroid/content/SharedPreferences;->getInt(Ljava/lang/String;I)I

    move-result v16

    .line 78
    .local v16, "companyId":I
    invoke-virtual/range {p1 .. p1}, Landroid/content/Context;->getContentResolver()Landroid/content/ContentResolver;

    move-result-object v9

    sget-object v10, Landroid/provider/CallLog$Calls;->CONTENT_URI:Landroid/net/Uri;

    const/4 v11, 0x0

    const/4 v12, 0x0

    const/4 v13, 0x0

    const-string v14, "date DESC"

    # Query latest call directly
    invoke-virtual/range {v9 .. v14}, Landroid/content/ContentResolver;->query(Landroid/net/Uri;[Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;)Landroid/database/Cursor;

    move-result-object v0

    .line 86
    .local v0, "cursor":Landroid/database/Cursor;
    if-eqz v0, :cond_4

    invoke-interface {v0}, Landroid/database/Cursor;->moveToFirst()Z

    move-result v4

    if-eqz v4, :cond_4

    .line 87
    const-string v4, "_id"

    invoke-interface {v0, v4}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v4

    invoke-interface {v0, v4}, Landroid/database/Cursor;->getString(I)Ljava/lang/String;

    move-result-object v10

    .line 88
    .local v10, "callId":Ljava/lang/String;
    const-string v4, "number"

    invoke-interface {v0, v4}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v4

    invoke-interface {v0, v4}, Landroid/database/Cursor;->getString(I)Ljava/lang/String;

    move-result-object v4

    .line 89
    .local v4, "number":Ljava/lang/String;
    const-string v5, "type"

    invoke-interface {v0, v5}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v5

    invoke-interface {v0, v5}, Landroid/database/Cursor;->getInt(I)I

    move-result v5

    .line 90
    .local v5, "type":I
    const-string v6, "duration"

    invoke-interface {v0, v6}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v6

    invoke-interface {v0, v6}, Landroid/database/Cursor;->getInt(I)I

    move-result v6

    .line 91
    .local v6, "duration":I
    const-string v9, "date"

    invoke-interface {v0, v9}, Landroid/database/Cursor;->getColumnIndexOrThrow(Ljava/lang/String;)I

    move-result v9

    invoke-interface {v0, v9}, Landroid/database/Cursor;->getLong(I)J

    move-result-wide v11

    move-wide v12, v11

    .line 94
    .local v12, "dateLong":J
    packed-switch v5, :pswitch_data_0

    .line 108
    :pswitch_0
    if-lez v6, :cond_2

    const-string v9, "answered"

    goto :goto_1

    .line 105
    :pswitch_1
    const-string v9, "incoming_rejected"

    .line 106
    .local v9, "typeStr":Ljava/lang/String;
    move-object v11, v9

    goto :goto_2

    .line 102
    .end local v9    # "typeStr":Ljava/lang/String;
    :pswitch_2
    const-string v9, "incoming_missed"

    .line 103
    .restart local v9    # "typeStr":Ljava/lang/String;
    move-object v11, v9

    goto :goto_2

    .line 96
    .end local v9    # "typeStr":Ljava/lang/String;
    :pswitch_3
    if-lez v6, :cond_1

    const-string v9, "outgoing_answered"

    goto :goto_0

    :cond_1
    const-string v9, "outgoing_no_answer"

    .line 97
    .restart local v9    # "typeStr":Ljava/lang/String;
    :goto_0
    move-object v11, v9

    goto :goto_2

    .line 99
    .end local v9    # "typeStr":Ljava/lang/String;
    :pswitch_4
    const-string v9, "incoming_answered"

    .line 100
    .restart local v9    # "typeStr":Ljava/lang/String;
    move-object v11, v9

    goto :goto_2

    .line 108
    .end local v9    # "typeStr":Ljava/lang/String;
    :cond_2
    const-string v9, "no_answer"

    :goto_1
    move-object v11, v9

    .line 112
    .local v11, "typeStr":Ljava/lang/String;
    :goto_2
    new-instance v9, Ljava/text/SimpleDateFormat;

    const-string v14, "yyyy-MM-dd HH:mm:ss"

    move-object/from16 v17, v3

    .end local v3    # "prefs":Landroid/content/SharedPreferences;
    .local v17, "prefs":Landroid/content/SharedPreferences;
    invoke-static {}, Ljava/util/Locale;->getDefault()Ljava/util/Locale;

    move-result-object v3

    invoke-direct {v9, v14, v3}, Ljava/text/SimpleDateFormat;-><init>(Ljava/lang/String;Ljava/util/Locale;)V

    move-object v3, v9

    .line 113
    .local v3, "sdf":Ljava/text/SimpleDateFormat;
    new-instance v9, Ljava/util/Date;

    invoke-direct {v9, v12, v13}, Ljava/util/Date;-><init>(J)V

    invoke-virtual {v3, v9}, Ljava/text/SimpleDateFormat;->format(Ljava/util/Date;)Ljava/lang/String;

    move-result-object v14

    .line 115
    .local v14, "startTime":Ljava/lang/String;
    new-instance v9, Lcom/diyacrm/dialer/OfflineDbHelper;

    invoke-direct {v9, v1}, Lcom/diyacrm/dialer/OfflineDbHelper;-><init>(Landroid/content/Context;)V

    .line 116
    .local v9, "db":Lcom/diyacrm/dialer/OfflineDbHelper;
    move-object/from16 v18, v11

    .end local v11    # "typeStr":Ljava/lang/String;
    .local v18, "typeStr":Ljava/lang/String;
    move-object v11, v4

    move-wide/from16 v19, v12

    .end local v12    # "dateLong":J
    .local v19, "dateLong":J
    move-object/from16 v12, v18

    move v13, v6

    # === DiyaCRM Safe SIM Filter ===
    # Check SIM filter safely without corrupting registers (v2 is free temp here)
    move-object/from16 v2, p1
    invoke-static {v2, v0}, Lcom/diyacrm/dialer/SimFilter;->shouldRecordCall(Landroid/content/Context;Landroid/database/Cursor;)Z
    move-result v2
    if-nez v2, :cond_4
    # If shouldRecordCall returned false (0), skip call (:cond_4). If true, continue!

    # Stop recording and trigger async upload
    invoke-static {}, Lcom/diyacrm/dialer/CallRecorder;->stop()Ljava/lang/String;
    move-object/from16 v2, p1
    invoke-static {v2, v10}, Lcom/diyacrm/dialer/UploadManager;->uploadRecordingAsync(Landroid/content/Context;Ljava/lang/String;)V
    # === End DiyaCRM Injection ===

    invoke-virtual/range {v9 .. v16}, Lcom/diyacrm/dialer/OfflineDbHelper;->insertCall(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;ILjava/lang/String;II)Z

    move-result v11

    .line 118
    .local v11, "inserted":Z
    if-eqz v11, :cond_3

    .line 119
    new-instance v12, Ljava/lang/StringBuilder;

    invoke-direct {v12}, Ljava/lang/StringBuilder;-><init>()V

    const-string v13, "Recorded Call: "

    invoke-virtual {v12, v13}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v12

    invoke-virtual {v12, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v12

    const-string v13, " ("

    invoke-virtual {v12, v13}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v12

    move-object/from16 v13, v18

    .end local v18    # "typeStr":Ljava/lang/String;
    .local v13, "typeStr":Ljava/lang/String;
    invoke-virtual {v12, v13}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v12

    const-string v1, ", "

    invoke-virtual {v12, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1, v6}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v12, "s)"

    invoke-virtual {v1, v12}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-static {v2, v1}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    .line 120
    invoke-static/range {p1 .. p1}, Lcom/diyacrm/dialer/SyncManager;->syncPendingCalls(Landroid/content/Context;)V

    goto :goto_3

    .line 118
    .end local v13    # "typeStr":Ljava/lang/String;
    .restart local v18    # "typeStr":Ljava/lang/String;
    :cond_3
    move-object/from16 v13, v18

    .line 122
    .end local v18    # "typeStr":Ljava/lang/String;
    .restart local v13    # "typeStr":Ljava/lang/String;
    invoke-interface {v0}, Landroid/database/Cursor;->close()V

    # Always ensure pending calls are synced to Odoo
    invoke-static/range {p1 .. p1}, Lcom/diyacrm/dialer/SyncManager;->syncPendingCalls(Landroid/content/Context;)V
    :try_end_0
    .catch Ljava/lang/SecurityException; {:try_start_0 .. :try_end_0} :catch_1
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    goto :goto_4

    .line 86
    .end local v4    # "number":Ljava/lang/String;
    .end local v5    # "type":I
    .end local v6    # "duration":I
    .end local v9    # "db":Lcom/diyacrm/dialer/OfflineDbHelper;
    .end local v10    # "callId":Ljava/lang/String;
    .end local v11    # "inserted":Z
    .end local v13    # "typeStr":Ljava/lang/String;
    .end local v14    # "startTime":Ljava/lang/String;
    .end local v17    # "prefs":Landroid/content/SharedPreferences;
    .end local v19    # "dateLong":J
    .local v3, "prefs":Landroid/content/SharedPreferences;
    :cond_4
    move-object/from16 v17, v3

    .end local v3    # "prefs":Landroid/content/SharedPreferences;
    .restart local v17    # "prefs":Landroid/content/SharedPreferences;
    goto :goto_4

    .line 126
    .end local v0    # "cursor":Landroid/database/Cursor;
    .end local v7    # "installTime":J
    .end local v15    # "userId":I
    .end local v16    # "companyId":I
    .end local v17    # "prefs":Landroid/content/SharedPreferences;
    :catch_0
    move-exception v0

    .line 127
    .local v0, "e":Ljava/lang/Exception;
    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "Error fetching call log: "

    invoke-virtual {v1, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v0}, Ljava/lang/Exception;->getMessage()Ljava/lang/String;

    move-result-object v3

    invoke-virtual {v1, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-static {v2, v1}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    goto :goto_5

    .line 124
    .end local v0    # "e":Ljava/lang/Exception;
    :catch_1
    move-exception v0

    .line 125
    .local v0, "se":Ljava/lang/SecurityException;
    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "Permission denied for CallLog: "

    invoke-virtual {v1, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v0}, Ljava/lang/SecurityException;->getMessage()Ljava/lang/String;

    move-result-object v3

    invoke-virtual {v1, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-static {v2, v1}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    .line 128
    .end local v0    # "se":Ljava/lang/SecurityException;
    :goto_4
    nop

    .line 129
    :goto_5
    return-void

    :pswitch_data_0
    .packed-switch 0x1
        :pswitch_4
        :pswitch_3
        :pswitch_2
        :pswitch_0
        :pswitch_1
    .end packed-switch
.end method

.method private synthetic lambda$onCallStateChanged$0(Landroid/content/Context;)V
    .locals 0
    .param p1, "context"    # Landroid/content/Context;

    .line 57
    invoke-direct {p0, p1}, Lcom/diyacrm/dialer/CallReceiver;->fetchLatestCallLog(Landroid/content/Context;)V

    return-void
.end method

.method private onCallStateChanged(Landroid/content/Context;I)V
    .locals 4
    .param p1, "context"    # Landroid/content/Context;
    .param p2, "state"    # I

    .line 45
    sget v0, Lcom/diyacrm/dialer/CallReceiver;->lastState:I

    if-ne v0, p2, :cond_0

    return-void

    .line 47
    :cond_0
    const/4 v0, 0x1

    packed-switch p2, :pswitch_data_0

    goto :goto_0

    .line 53
    :pswitch_0
    # === DiyaCRM: Start recording on OFFHOOK ===
    invoke-static {p1}, Lcom/diyacrm/dialer/CallRecorder;->start(Landroid/content/Context;)V
    # === End recording start ===
    goto :goto_0

    .line 49
    :pswitch_1
    sput-boolean v0, Lcom/diyacrm/dialer/CallReceiver;->isIncoming:Z

    .line 50
    goto :goto_0

    .line 56
    :pswitch_2
    sget v1, Lcom/diyacrm/dialer/CallReceiver;->lastState:I

    const/4 v2, 0x2

    if-eq v1, v2, :cond_1

    sget v1, Lcom/diyacrm/dialer/CallReceiver;->lastState:I

    if-ne v1, v0, :cond_2

    .line 57
    :cond_1
    new-instance v0, Landroid/os/Handler;

    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;

    move-result-object v1

    invoke-direct {v0, v1}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V

    new-instance v1, Lcom/diyacrm/dialer/CallReceiver$$ExternalSyntheticLambda0;

    invoke-direct {v1, p0, p1}, Lcom/diyacrm/dialer/CallReceiver$$ExternalSyntheticLambda0;-><init>(Lcom/diyacrm/dialer/CallReceiver;Landroid/content/Context;)V

    const-wide/16 v2, 0x5dc

    invoke-virtual {v0, v1, v2, v3}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    .line 59
    :cond_2
    const/4 v0, 0x0

    sput-boolean v0, Lcom/diyacrm/dialer/CallReceiver;->isIncoming:Z

    .line 62
    :goto_0
    sput p2, Lcom/diyacrm/dialer/CallReceiver;->lastState:I

    .line 63
    return-void

    :pswitch_data_0
    .packed-switch 0x0
        :pswitch_2
        :pswitch_1
        :pswitch_0
    .end packed-switch
.end method


# virtual methods
.method public onReceive(Landroid/content/Context;Landroid/content/Intent;)V
    .locals 4
    .param p1, "context"    # Landroid/content/Context;
    .param p2, "intent"    # Landroid/content/Intent;

    .line 24
    invoke-virtual {p2}, Landroid/content/Intent;->getAction()Ljava/lang/String;

    move-result-object v0

    .line 25
    .local v0, "action":Ljava/lang/String;
    const-string v1, "android.intent.action.NEW_OUTGOING_CALL"

    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1

    if-eqz v1, :cond_0

    .line 26
    const/4 v1, 0x0

    sput-boolean v1, Lcom/diyacrm/dialer/CallReceiver;->isIncoming:Z

    goto :goto_1

    .line 27
    :cond_0
    const-string v1, "android.intent.action.PHONE_STATE"

    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1

    if-eqz v1, :cond_3

    .line 28
    const-string v1, "state"

    invoke-virtual {p2, v1}, Landroid/content/Intent;->getStringExtra(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v1

    .line 29
    .local v1, "stateStr":Ljava/lang/String;
    const/4 v2, 0x0

    .line 31
    .local v2, "state":I
    sget-object v3, Landroid/telephony/TelephonyManager;->EXTRA_STATE_RINGING:Ljava/lang/String;

    invoke-virtual {v3, v1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v3

    if-eqz v3, :cond_1

    .line 32
    const/4 v2, 0x1

    .line 33
    const/4 v3, 0x1

    sput-boolean v3, Lcom/diyacrm/dialer/CallReceiver;->isIncoming:Z

    goto :goto_0

    .line 34
    :cond_1
    sget-object v3, Landroid/telephony/TelephonyManager;->EXTRA_STATE_OFFHOOK:Ljava/lang/String;

    invoke-virtual {v3, v1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v3

    if-eqz v3, :cond_2

    .line 35
    const/4 v2, 0x2

    goto :goto_0

    .line 36
    :cond_2
    sget-object v3, Landroid/telephony/TelephonyManager;->EXTRA_STATE_IDLE:Ljava/lang/String;

    invoke-virtual {v3, v1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    .line 37
    const/4 v2, 0x0

    .line 40
    :goto_0
    invoke-direct {p0, p1, v2}, Lcom/diyacrm/dialer/CallReceiver;->onCallStateChanged(Landroid/content/Context;I)V

    .line 42
    .end local v1    # "stateStr":Ljava/lang/String;
    .end local v2    # "state":I
    :cond_3
    :goto_1
    return-void
.end method
