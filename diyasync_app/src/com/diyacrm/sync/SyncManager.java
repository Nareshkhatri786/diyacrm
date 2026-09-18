package com.diyacrm.sync;

import android.content.Context;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.net.Uri;
import android.provider.DocumentsContract;
import android.util.Log;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class SyncManager {
    private static final String TAG = "DiyaSync";
    private static final Pattern PHONE_PATTERN = Pattern.compile("(\\d{10,12})");

    public static int performSync(Context context) {
        SharedPreferences prefs = context.getSharedPreferences("DiyaSync_Prefs", Context.MODE_PRIVATE);
        String serverUrl = prefs.getString("server_url", "https://crm.sigprop.in");
        int userId = prefs.getInt("user_id", 0);
        int companyId = prefs.getInt("company_id", 0);
        String folderUriStr = prefs.getString("folder_uri", "");

        if (userId <= 0 || folderUriStr == null || folderUriStr.isEmpty()) {
            Log.d(TAG, "Sync skipped: user not logged in or folder not selected");
            return 0;
        }

        Uri treeUri = Uri.parse(folderUriStr);
        SyncDbHelper db = new SyncDbHelper(context);
        int uploadedCount = 0;

        try {
            String treeDocId = DocumentsContract.getTreeDocumentId(treeUri);
            uploadedCount = scanAndUploadDirectory(context, treeUri, treeDocId, null, serverUrl, userId, companyId, db);
        } catch (Exception e) {
            Log.e(TAG, "Sync Error", e);
        }

        return uploadedCount;
    }

    private static int scanAndUploadDirectory(Context context, Uri treeUri, String parentDocId, String parentDirName,
                                              String serverUrl, int userId, int companyId, SyncDbHelper db) {
        int count = 0;
        Cursor c = null;
        try {
            Uri childrenUri = DocumentsContract.buildChildDocumentsUriUsingTree(treeUri, parentDocId);
            c = context.getContentResolver().query(
                    childrenUri,
                    new String[]{
                            DocumentsContract.Document.COLUMN_DOCUMENT_ID,
                            DocumentsContract.Document.COLUMN_DISPLAY_NAME,
                            DocumentsContract.Document.COLUMN_MIME_TYPE,
                            DocumentsContract.Document.COLUMN_LAST_MODIFIED
                    },
                    null, null, null
            );

            if (c != null && c.moveToFirst()) {
                do {
                    String docId = c.getString(0);
                    String displayName = c.getString(1);
                    String mimeType = c.getString(2);

                    if (DocumentsContract.Document.MIME_TYPE_DIR.equals(mimeType)) {
                        // Recurse into subdirectories (e.g. Infinix PhoneRecord/<phone_number>/)
                        count += scanAndUploadDirectory(context, treeUri, docId, displayName, serverUrl, userId, companyId, db);
                    } else if (isAudioFile(displayName)) {
                        // Check if already synced
                        String uniqueKey = treeUri.toString() + "::" + docId;
                        if (!db.isAlreadySynced(uniqueKey)) {
                            String phone = extractPhoneNumber(parentDirName, displayName);
                            Uri fileUri = DocumentsContract.buildDocumentUriUsingTree(treeUri, docId);
                            boolean success = uploadFileStream(context, fileUri, displayName, phone, serverUrl, userId, companyId);
                            if (success) {
                                db.markSynced(uniqueKey, displayName, phone);
                                count++;
                                Log.i(TAG, "Uploaded recording: " + displayName + " for phone: " + phone);
                            }
                        }
                    }
                } while (c.moveToNext());
            }
        } catch (Exception e) {
            Log.e(TAG, "Directory scan error for docId: " + parentDocId, e);
        } finally {
            if (c != null) c.close();
        }
        return count;
    }

    private static boolean isAudioFile(String name) {
        if (name == null) return false;
        String lower = name.toLowerCase();
        return lower.endsWith(".aac") || lower.endsWith(".m4a") || lower.endsWith(".mp3")
                || lower.endsWith(".amr") || lower.endsWith(".wav") || lower.endsWith(".ogg");
    }

    private static String extractPhoneNumber(String parentDirName, String filename) {
        // 1. Infinix style: parent directory is the phone number e.g. "9574466663"
        if (parentDirName != null && !parentDirName.isEmpty()) {
            String digits = parentDirName.replaceAll("\\D", "");
            if (digits.length() >= 10) {
                return digits.length() > 10 ? digits.substring(digits.length() - 10) : digits;
            }
        }

        // 2. Check filename for phone digits
        if (filename != null) {
            Matcher m = PHONE_PATTERN.matcher(filename);
            if (m.find()) {
                String match = m.group(1);
                if (match.length() > 10) match = match.substring(match.length() - 10);
                return match;
            }
        }

        return "Unknown";
    }

    private static boolean uploadFileStream(Context context, Uri fileUri, String filename, String phone,
                                           String serverUrl, int userId, int companyId) {
        InputStream is = null;
        OutputStream os = null;
        HttpURLConnection conn = null;
        try {
            is = context.getContentResolver().openInputStream(fileUri);
            if (is == null) return false;

            String uploadEndpoint = serverUrl.replaceAll("/+$", "") + "/api/call_tracker/upload_recording";
            URL url = new URL(uploadEndpoint);
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            conn.setConnectTimeout(20000);
            conn.setReadTimeout(45000);

            conn.setRequestProperty("Content-Type", "application/octet-stream");
            conn.setRequestProperty("X-Call-Id", phone);
            conn.setRequestProperty("X-User-Id", String.valueOf(userId));
            conn.setRequestProperty("X-Company-Id", String.valueOf(companyId));
            conn.setRequestProperty("X-Filename", filename);

            os = conn.getOutputStream();
            byte[] buffer = new byte[8192];
            int bytesRead;
            while ((bytesRead = is.read(buffer)) != -1) {
                os.write(buffer, 0, bytesRead);
            }
            os.flush();

            int code = conn.getResponseCode();
            return code == 200 || code == 201;

        } catch (Exception e) {
            Log.e(TAG, "Upload failed for " + filename, e);
            return false;
        } finally {
            try { if (is != null) is.close(); } catch (Exception ignored) {}
            try { if (os != null) os.close(); } catch (Exception ignored) {}
            if (conn != null) conn.disconnect();
        }
    }
}
