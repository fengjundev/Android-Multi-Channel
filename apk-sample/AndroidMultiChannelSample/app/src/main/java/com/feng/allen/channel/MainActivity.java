package com.feng.allen.channel;

import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.support.v7.app.AppCompatActivity;
import android.widget.TextView;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        TextView tv = (TextView) findViewById(R.id.channel_tv);

        tv.setText(getMetaValue(getApplicationContext(), "CHANNEL_ID", "Can not get CHANNEL_ID"));
    }

    public String getMetaValue(Context context, String keyName, String defValue) {
        Object value = null;
        ApplicationInfo applicationInfo;
        try {
            applicationInfo = context.getPackageManager().getApplicationInfo(context
                    .getPackageName(), PackageManager.GET_META_DATA);

            value = applicationInfo.metaData.get(keyName);

        } catch (Exception e) {
            e.printStackTrace();
        }
        if (value != null) {
            return value.toString();
        } else {
            return defValue;
        }

    }
}
