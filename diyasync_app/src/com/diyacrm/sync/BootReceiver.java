package com.diyacrm.sync;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        SharedPreferences prefs = context.getSharedPreferences("DiyaSync_Prefs", Context.MODE_PRIVATE);
        int userId = prefs.getInt("user_id", 0);
        String folderUri = prefs.getString("folder_uri", "");
        if (userId > 0 && folderUri != null && !folderUri.isEmpty()) {
            SyncService.start(context);
        }
    }
}
