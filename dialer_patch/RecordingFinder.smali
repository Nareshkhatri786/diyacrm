.class public Lcom/diyacrm/dialer/RecordingFinder;
.super Ljava/lang/Object;
.source "RecordingFinder.java"


# static fields
.field private static final TAG:Ljava/lang/String; = "DiyaCRMRecFinder"


# direct methods
.method public constructor <init>()V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method public static getCustomFolder(Landroid/content/Context;)Ljava/lang/String;
    .locals 3

    const-string v0, "DiyaCRM_Prefs"

    const/4 v1, 0x0

    invoke-virtual {p0, v0, v1}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    const-string v1, "custom_recording_dir"

    const-string v2, ""

    invoke-interface {v0, v1, v2}, Landroid/content/SharedPreferences;->getString(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v0

    return-object v0
.end method

.method public static setCustomFolder(Landroid/content/Context;Ljava/lang/String;)V
    .locals 2

    const-string v0, "DiyaCRM_Prefs"

    const/4 v1, 0x0

    invoke-virtual {p0, v0, v1}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    invoke-interface {v0}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    const-string v1, "custom_recording_dir"

    invoke-interface {v0, v1, p1}, Landroid/content/SharedPreferences$Editor;->putString(Ljava/lang/String;Ljava/lang/String;)Landroid/content/SharedPreferences$Editor;

    move-result-object v0

    invoke-interface {v0}, Landroid/content/SharedPreferences$Editor;->apply()V

    return-void
.end method

.method private static isAudioFile(Ljava/lang/String;)Z
    .locals 2

    const/4 v0, 0x0

    if-nez p0, :cond_0

    return v0

    :cond_0
    invoke-virtual {p0}, Ljava/lang/String;->toLowerCase()Ljava/lang/String;

    move-result-object p0

    const-string v1, ".aac"

    invoke-virtual {p0, v1}, Ljava/lang/String;->endsWith(Ljava/lang/String;)Z

    move-result v1

    if-nez v1, :cond_1

    const-string v1, ".m4a"

    invoke-virtual {p0, v1}, Ljava/lang/String;->endsWith(Ljava/lang/String;)Z

    move-result v1

    if-nez v1, :cond_1

    const-string v1, ".mp3"

    invoke-virtual {p0, v1}, Ljava/lang/String;->endsWith(Ljava/lang/String;)Z

    move-result v1

    if-nez v1, :cond_1

    const-string v1, ".amr"

    invoke-virtual {p0, v1}, Ljava/lang/String;->endsWith(Ljava/lang/String;)Z

    move-result v1

    if-nez v1, :cond_1

    const-string v1, ".wav"

    invoke-virtual {p0, v1}, Ljava/lang/String;->endsWith(Ljava/lang/String;)Z

    move-result p0

    if-eqz p0, :cond_2

    :cond_1
    const/4 v0, 0x1

    :cond_2
    return v0
.end method

.method private static scanDirectory(Ljava/io/File;Ljava/lang/String;J)Ljava/lang/String;
    .locals 10

    const/4 v0, 0x0

    if-eqz p0, :cond_7

    invoke-virtual {p0}, Ljava/io/File;->exists()Z

    move-result v1

    if-eqz v1, :cond_7

    invoke-virtual {p0}, Ljava/io/File;->isDirectory()Z

    move-result v1

    if-nez v1, :cond_0

    goto :goto_2

    :cond_0
    invoke-virtual {p0}, Ljava/io/File;->listFiles()[Ljava/io/File;

    move-result-object p0

    if-nez p0, :cond_1

    return-object v0

    :cond_1
    array-length v1, p0

    const/4 v2, 0x0

    :goto_0
    if-ge v2, v1, :cond_7

    aget-object v3, p0, v2

    if-eqz v3, :cond_6

    invoke-virtual {v3}, Ljava/io/File;->isFile()Z

    move-result v4

    if-eqz v4, :cond_6

    invoke-virtual {v3}, Ljava/io/File;->length()J

    move-result-wide v4

    const-wide/16 v6, 0x0

    cmp-long v4, v4, v6

    if-lez v4, :cond_6

    invoke-virtual {v3}, Ljava/io/File;->getName()Ljava/lang/String;

    move-result-object v4

    invoke-static {v4}, Lcom/diyacrm/dialer/RecordingFinder;->isAudioFile(Ljava/lang/String;)Z

    move-result v5

    if-nez v5, :cond_2

    goto :goto_1

    :cond_2
    # Check phone match
    if-eqz p1, :cond_4

    invoke-virtual {p1}, Ljava/lang/String;->isEmpty()Z

    move-result v5

    if-nez v5, :cond_4

    invoke-virtual {v4, p1}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z

    move-result v4

    if-nez v4, :cond_3

    invoke-virtual {v3}, Ljava/io/File;->getParent()Ljava/lang/String;

    move-result-object v4

    if-eqz v4, :cond_4

    invoke-virtual {v4, p1}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z

    move-result v4

    if-eqz v4, :cond_4

    :cond_3
    invoke-virtual {v3}, Ljava/io/File;->getAbsolutePath()Ljava/lang/String;

    move-result-object p0

    return-object p0

    :cond_4
    # Time match within 15 minutes (900000 ms)
    cmp-long v4, p2, v6

    if-lez v4, :cond_6

    invoke-virtual {v3}, Ljava/io/File;->lastModified()J

    move-result-wide v4

    sub-long/2addr v4, p2

    invoke-static {v4, v5}, Ljava/lang/Math;->abs(J)J

    move-result-wide v4

    const-wide/32 v6, 0xdbba0

    cmp-long v4, v4, v6

    if-gez v4, :cond_6

    if-nez v0, :cond_5

    invoke-virtual {v3}, Ljava/io/File;->getAbsolutePath()Ljava/lang/String;

    move-result-object v0

    :cond_5
    return-object v0

    :cond_6
    :goto_1
    add-int/lit8 v2, v2, 0x1

    goto :goto_0

    :cond_7
    :goto_2
    return-object v0
.end method

.method public static findRecordingForCall(Landroid/content/Context;Ljava/lang/String;J)Ljava/lang/String;
    .locals 6

    const-string v0, "DiyaCRMRecFinder"

    const/4 v1, 0x0

    :try_start_0
    # Clean phone to 10 digits
    const-string v2, ""

    if-eqz p1, :cond_0

    const-string v3, "\\D"

    invoke-virtual {p1, v3, v2}, Ljava/lang/String;->replaceAll(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v2

    invoke-virtual {v2}, Ljava/lang/String;->length()I

    move-result v3

    const/16 v4, 0xa

    if-le v3, v4, :cond_0

    sub-int/2addr v3, v4

    invoke-virtual {v2, v3}, Ljava/lang/String;->substring(I)Ljava/lang/String;

    move-result-object v2

    :cond_0
    # 1. Check custom folder
    invoke-static {p0}, Lcom/diyacrm/dialer/RecordingFinder;->getCustomFolder(Landroid/content/Context;)Ljava/lang/String;

    move-result-object p0

    if-eqz p0, :cond_1

    invoke-virtual {p0}, Ljava/lang/String;->isEmpty()Z

    move-result v3

    if-nez v3, :cond_1

    new-instance v3, Ljava/io/File;

    invoke-direct {v3, p0}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-static {v3, v2, p2, p3}, Lcom/diyacrm/dialer/RecordingFinder;->scanDirectory(Ljava/io/File;Ljava/lang/String;J)Ljava/lang/String;

    move-result-object p0

    if-eqz p0, :cond_1

    return-object p0

    :cond_1
    # 2. Check Infinix/Tecno subfolder: /storage/emulated/0/Music/PhoneRecord/<phone>
    new-instance p0, Ljava/lang/StringBuilder;

    invoke-direct {p0}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "/storage/emulated/0/Music/PhoneRecord/"

    invoke-virtual {p0, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    new-instance v3, Ljava/io/File;

    invoke-direct {v3, p0}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-static {v3, v2, p2, p3}, Lcom/diyacrm/dialer/RecordingFinder;->scanDirectory(Ljava/io/File;Ljava/lang/String;J)Ljava/lang/String;

    move-result-object p0

    if-eqz p0, :cond_2

    return-object p0

    # 3. Check /storage/emulated/0/Music/PhoneRecord
    :cond_2
    new-instance p0, Ljava/io/File;

    const-string v3, "/storage/emulated/0/Music/PhoneRecord"

    invoke-direct {p0, v3}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-static {p0, v2, p2, p3}, Lcom/diyacrm/dialer/RecordingFinder;->scanDirectory(Ljava/io/File;Ljava/lang/String;J)Ljava/lang/String;

    move-result-object p0

    if-eqz p0, :cond_3

    return-object p0

    # 4. Check Samsung / OnePlus: /storage/emulated/0/Recordings/Call
    :cond_3
    new-instance p0, Ljava/io/File;

    const-string v3, "/storage/emulated/0/Recordings/Call"

    invoke-direct {p0, v3}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-static {p0, v2, p2, p3}, Lcom/diyacrm/dialer/RecordingFinder;->scanDirectory(Ljava/io/File;Ljava/lang/String;J)Ljava/lang/String;

    move-result-object p0

    if-eqz p0, :cond_4

    return-object p0

    # 5. Check Xiaomi / Redmi: /storage/emulated/0/MIUI/sound_recorder/call_rec
    :cond_4
    new-instance p0, Ljava/io/File;

    const-string v3, "/storage/emulated/0/MIUI/sound_recorder/call_rec"

    invoke-direct {p0, v3}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-static {p0, v2, p2, p3}, Lcom/diyacrm/dialer/RecordingFinder;->scanDirectory(Ljava/io/File;Ljava/lang/String;J)Ljava/lang/String;

    move-result-object p0

    if-eqz p0, :cond_5

    return-object p0

    # 6. Check Vivo / Oppo: /storage/emulated/0/Recordings
    :cond_5
    new-instance p0, Ljava/io/File;

    const-string v3, "/storage/emulated/0/Recordings"

    invoke-direct {p0, v3}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-static {p0, v2, p2, p3}, Lcom/diyacrm/dialer/RecordingFinder;->scanDirectory(Ljava/io/File;Ljava/lang/String;J)Ljava/lang/String;

    move-result-object p0

    if-eqz p0, :cond_6

    return-object p0

    # 7. Check /storage/emulated/0/PhoneRecord
    :cond_6
    new-instance p0, Ljava/io/File;

    const-string v3, "/storage/emulated/0/PhoneRecord"

    invoke-direct {p0, v3}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    invoke-static {p0, v2, p2, p3}, Lcom/diyacrm/dialer/RecordingFinder;->scanDirectory(Ljava/io/File;Ljava/lang/String;J)Ljava/lang/String;

    move-result-object p0
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    if-eqz p0, :cond_7

    return-object p0

    :cond_7
    return-object v1

    :catch_0
    move-exception p0

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "Error finding recording: "

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {p0}, Ljava/lang/Exception;->getMessage()Ljava/lang/String;

    move-result-object p0

    invoke-virtual {v2, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-static {v0, p0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    return-object v1
.end method
