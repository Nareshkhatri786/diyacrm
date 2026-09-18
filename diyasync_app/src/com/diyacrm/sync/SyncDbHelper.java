package com.diyacrm.sync;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import org.json.JSONArray;
import org.json.JSONObject;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class SyncDbHelper extends SQLiteOpenHelper {
    private static final String DB_NAME = "diyasync.db";
    private static final int DB_VERSION = 1;

    private static final String TABLE_SYNCED = "synced_recordings";
    private static final String COL_DOC_URI = "doc_uri";
    private static final String COL_FILENAME = "filename";
    private static final String COL_PHONE = "phone";
    private static final String COL_TIMESTAMP = "sync_timestamp";

    public SyncDbHelper(Context context) {
        super(context, DB_NAME, null, DB_VERSION);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE IF NOT EXISTS " + TABLE_SYNCED + " (" +
                COL_DOC_URI + " TEXT PRIMARY KEY, " +
                COL_FILENAME + " TEXT, " +
                COL_PHONE + " TEXT, " +
                COL_TIMESTAMP + " INTEGER)");
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        db.execSQL("DROP TABLE IF EXISTS " + TABLE_SYNCED);
        onCreate(db);
    }

    public synchronized boolean isAlreadySynced(String docUri) {
        if (docUri == null) return false;
        SQLiteDatabase db = getReadableDatabase();
        Cursor cursor = null;
        try {
            cursor = db.query(TABLE_SYNCED, new String[]{COL_DOC_URI},
                    COL_DOC_URI + "=?", new String[]{docUri}, null, null, null);
            return cursor != null && cursor.moveToFirst();
        } catch (Exception e) {
            return false;
        } finally {
            if (cursor != null) cursor.close();
        }
    }

    public synchronized void markSynced(String docUri, String filename, String phone) {
        if (docUri == null) return;
        SQLiteDatabase db = getWritableDatabase();
        try {
            ContentValues cv = new ContentValues();
            cv.put(COL_DOC_URI, docUri);
            cv.put(COL_FILENAME, filename);
            cv.put(COL_PHONE, phone);
            cv.put(COL_TIMESTAMP, System.currentTimeMillis());
            db.insertWithOnConflict(TABLE_SYNCED, null, cv, SQLiteDatabase.CONFLICT_REPLACE);
        } catch (Exception ignored) {}
    }

    public synchronized int getSyncedCount() {
        SQLiteDatabase db = getReadableDatabase();
        Cursor cursor = null;
        try {
            cursor = db.rawQuery("SELECT COUNT(*) FROM " + TABLE_SYNCED, null);
            if (cursor != null && cursor.moveToFirst()) {
                return cursor.getInt(0);
            }
        } catch (Exception ignored) {
        } finally {
            if (cursor != null) cursor.close();
        }
        return 0;
    }

    public synchronized String getRecentLogsJson() {
        JSONArray arr = new JSONArray();
        SQLiteDatabase db = getReadableDatabase();
        Cursor cursor = null;
        SimpleDateFormat sdf = new SimpleDateFormat("dd MMM, hh:mm a", Locale.getDefault());
        try {
            cursor = db.query(TABLE_SYNCED, null, null, null, null, null, COL_TIMESTAMP + " DESC", "15");
            if (cursor != null && cursor.moveToFirst()) {
                do {
                    JSONObject obj = new JSONObject();
                    obj.put("filename", cursor.getString(cursor.getColumnIndexOrThrow(COL_FILENAME)));
                    obj.put("phone", cursor.getString(cursor.getColumnIndexOrThrow(COL_PHONE)));
                    long ts = cursor.getLong(cursor.getColumnIndexOrThrow(COL_TIMESTAMP));
                    obj.put("time", sdf.format(new Date(ts)));
                    arr.put(obj);
                } while (cursor.moveToNext());
            }
        } catch (Exception ignored) {
        } finally {
            if (cursor != null) cursor.close();
        }
        return arr.toString();
    }
}
