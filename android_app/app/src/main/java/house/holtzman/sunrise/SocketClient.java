package house.holtzman.sunrise;


import android.content.Context;
import android.content.SharedPreferences;
import android.os.AsyncTask;
import android.preference.PreferenceManager;
import android.util.Log;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.net.ConnectException;
import java.net.InetAddress;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.net.UnknownHostException;

/**
 * Created by Filippo on 11/10/2015.
 */
public class SocketClient extends AsyncTask<String, Void, String> {
    private int SERVER_PORT; // = 8080;
    private String SERVER_IP; // = "192.168.1.132";
    private static final String TAG = "SocketClient";
    private Socket socket;
    public PrintWriter out;
    public BufferedReader in;

    private MyFragmentTemplate.FragmentCallback mCallback;
    private String cmd;
    private Context context;
    private boolean isAfterReset = false;

    public SocketClient(Context context, String cmd, MyFragmentTemplate.FragmentCallback fragmentCallback) {
        setup(context, cmd, fragmentCallback);
    }

    public SocketClient(Context context, String cmd, boolean isAfterReset, MyFragmentTemplate.FragmentCallback fragmentCallback) {
        setup(context, cmd, fragmentCallback);
        this.isAfterReset = isAfterReset;
    }

    private void setup(Context context, String cmd, MyFragmentTemplate.FragmentCallback fragmentCallback) {
        Log.i(TAG, "Creating SocketClient with cmd = " + cmd);
        this.mCallback = fragmentCallback;
        this.cmd = cmd;
        this.context = context;
        SharedPreferences SP = PreferenceManager.getDefaultSharedPreferences(this.context);
        this.SERVER_IP = SP.getString("pref_ip_address", "config not set!");
        this.SERVER_PORT = Integer.valueOf(SP.getString("pref_port", "0"));
    }

    @Override
    protected String doInBackground(String... args) {
        String result = "";
        String line;

        try {
            Log.i(TAG, "Creating socket");
            InetAddress serverAddr = InetAddress.getByName(SERVER_IP);
            Log.i(TAG, "serverAddr=" + serverAddr.toString());
            socket = new Socket(serverAddr, SERVER_PORT);
            socket.setSoTimeout(5000);
            Log.i(TAG, "Socket created");
        } catch (UnknownHostException e) {
            Log.e(TAG, e.toString());
            return null;
        } catch (ConnectException e) {
            Log.e(TAG, e.toString());
            return null;
        } catch (IOException e) {
            Log.e(TAG, e.toString());
        }

        try {
            Log.i(TAG, "Creating print writer");
            out = new PrintWriter(new BufferedWriter(new OutputStreamWriter(socket.getOutputStream())), true);
            try {
                in = new BufferedReader(new InputStreamReader(socket.getInputStream()));
            }
            catch (SocketTimeoutException e) {
                Log.i(TAG, "Socket timed out");
                return null;
            }

            if (this.isAfterReset) {
                try {
                    Log.i(TAG, "Catching startup message");
                    result = "";
                    while (!(line = in.readLine()).equals("@#$")) {
                        result = result + line + "\n";
                    }

                    result = result.trim();
                    //                result = result.replace("null", "");
                    Log.i(TAG, "startup message=" + result);
                    if (result.endsWith("Run")) {
                        Log.i(TAG, "Startup complete");
                    }
                } catch (IOException e) {
                    Log.i(TAG, "IOException in startup message checking");
                }
            }

            Log.i(TAG, "Sending cmd = " + this.cmd);
            out.println(this.cmd);
            Log.i(TAG, "command sent");

            result = "";
            while (!(line = in.readLine()).equals("@#$")) {
                result = result + line + "\n";
            }
            result = result.trim();
//            result = result.replace("null", "");
            Log.i(TAG, "result=" + result);

        } catch (IOException e) {
            Log.i(TAG, "caught IOexception", e);
        }
        finally {
            if (socket != null) {
                try {
                    socket.close();
                    Log.i(TAG, "socket closed");
                }
                catch (IOException e) {

                }
            }
        }

        return result;//returns what you want to pass to the onPostExecute()

        //Test code that bypasses socket
//        try {
//            Time now = new Time();
//            switch (this.cmd) {
//                case "RT+":
//                    Thread.sleep(1000);
//                    now.setToNow();
//
//                    return now.toString();
//
//                case "ST+":
//                    Thread.sleep(2000);
//                    now.setToNow();
//
//                    return now.toString();
//
//                case "RA+":
//                    Thread.sleep(1000);
//                    return "0,6,10,0,wakeup,1,0\n3,7,10,18,wakeup,1,1";
////                    return "No Alarms";
//
//                case "WA+":
//                    Thread.sleep(3000);
//                    return "WipingAlarms...\nAlarms Wiped\nDeactivating Program\nRun";
//
//                case "XA+0":
//                    Thread.sleep(3000);
//                    return "Deleting Timer...\nTimer Deleted\nDeactivating Program\nRun";
//
//                case "XA+1":
//                    Thread.sleep(3000);
//                    return "Deleting Timer...\nTimer Deleted\nDeactivating Program\nRun";
//
//                case "XA+2":
//                    Thread.sleep(3000);
//                    return "Deleting Timer...\nTimer does not exist";
//
//                case "DP+":
//                    Thread.sleep(1000);
//
//                    return "Deactivating Program";
//
//                case "AP+wakeup":
//                    Thread.sleep(1000);
//
//                    return "Running Wakeup";
//            }
//        } catch (InterruptedException e) {
//            return "";
//        }
//
//        return "";
    }

    @Override
    protected void onPostExecute(String result) {
        this.mCallback.onTaskDone(result);
    }

}
