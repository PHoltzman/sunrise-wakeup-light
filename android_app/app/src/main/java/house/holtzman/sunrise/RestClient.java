package house.holtzman.sunrise;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.preference.PreferenceManager;
import android.util.Log;

import com.android.volley.Request;
import com.android.volley.RequestQueue;
import com.android.volley.Response;
import com.android.volley.VolleyError;
import com.android.volley.toolbox.JsonObjectRequest;
import com.android.volley.toolbox.JsonRequest;
import com.android.volley.toolbox.Volley;

import org.json.JSONException;
import org.json.JSONObject;

/**
 * Created by Filippo on 2/1/2018.
 */
public class RestClient {
    private int SERVER_PORT;
    private String SERVER_IP;
    private String baseUrl;
    private Context context;
    private Activity activity;
    private static final String TAG = "RestClient";

    RestClient(Context context, Activity activity){
        SharedPreferences SP = PreferenceManager.getDefaultSharedPreferences(context);
        this.SERVER_IP = SP.getString("pref_ip_address", "config not set!");
        this.SERVER_PORT = Integer.valueOf(SP.getString("pref_port", "0"));
        this.baseUrl = "http://" + this.SERVER_IP + ':' + this.SERVER_PORT + '/';
        this.context = context;
        this.activity = activity;
    }

    public void request(int method, String path, JSONObject args, final VolleyCallback callback) {
        RequestQueue queue = Volley.newRequestQueue(this.context);
        String url = this.baseUrl + path;
        final Activity lActivity= this.activity;

        Log.d(TAG, String.format("Making %s request to %s", String.valueOf(method), url));
        if (args != null) {
            Log.d(TAG, String.format("Arguments are: %s", args.toString()));
        }

        JsonObjectRequestAllowEmpty request = new JsonObjectRequestAllowEmpty(method, url, args,
                new Response.Listener<JSONObject>() {
                    @Override
                    public void onResponse(JSONObject response) {
                        callback.onSuccessResponse(response);
                    }
                },
                new Response.ErrorListener() {
                    @Override
                    public void onErrorResponse(VolleyError error) {
                        Log.i(TAG, error.toString());
                        new Notifier(lActivity, "Error while executing request.").show();
                    }
                }
        );

        queue.add(request);

    }

    public void getRequest(String path, final VolleyCallback callback) {
        getRequest(path, null, callback);
    }

    public void getRequest(String path, JSONObject args, final VolleyCallback callback) {
        request(Request.Method.GET, path, args, callback);
    }

    public void deleteRequest(String path, final VolleyCallback callback) {
        request(Request.Method.DELETE, path, null, callback);
    }

    public void postRequest(String path, JSONObject postBody, final VolleyCallback callback) {
        request(Request.Method.POST, path, postBody, callback);
    }
}
