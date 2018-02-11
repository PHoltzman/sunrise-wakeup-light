package house.holtzman.sunrise;

import android.content.Context;
import android.util.Log;
import android.widget.Toast;

import com.google.gson.Gson;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Created by Filippo on 11/8/2015.
 */
public class Timer {
    private static final String TAG = "Timer";

    private String id;
    private boolean isEnabled;
    private int hour;
    private int minute;
    private List<String> timerSchedule;
    private String funcName;
    private HashMap<String,String> arguments;

    public Timer(String timerId, boolean isEnabled, int hour, int minute, List timerSchedule, String funcName, HashMap<String, String> arguments) {
        this.id = timerId;
        this.isEnabled = isEnabled;
        this.hour = hour;
        this.minute = minute;
        this.timerSchedule = timerSchedule;
        this.funcName = funcName;
        this.arguments = arguments;
    }

    public Timer(JSONObject payload) {
        try {
            this.id = payload.get("timerId").toString();
            this.isEnabled = (boolean)payload.get("isEnabled");
            this.hour = (int)payload.get("triggerHour");
            this.minute = (int)payload.get("triggerMinute");
            this.funcName = payload.get("programToLaunch").toString();
            this.arguments = null;//(HashMap<String, String>) payload.get("arguments");

            ArrayList<String> listdata = new ArrayList<String>();
            JSONArray jArray = (JSONArray)payload.get("timerSchedule");
            if (jArray != null) {
                for (int i=0;i<jArray.length();i++){
                    listdata.add(jArray.getString(i));
                }
            }
            this.timerSchedule = listdata;
        }
        catch (JSONException e) {
            Log.e(TAG,e.getMessage());
        }
    }

    public HashMap<String, Object> toJson() {
        HashMap<String, Object> jsonMap = new HashMap<>();
        jsonMap.put("timerId", this.id);
        jsonMap.put("isEnabled", this.isEnabled);
        jsonMap.put("triggerHour", this.hour);
        jsonMap.put("triggerMinute", this.minute);
        jsonMap.put("programToLaunch", this.funcName);
        jsonMap.put("timerSchedule", this.timerSchedule);
        jsonMap.put("arguments", this.arguments);

        return jsonMap;
    }

    public String makeTimerScheduleString() {
        String theString = "";
        String abbrev = "";
        for (String day : this.timerSchedule) {
            if (day.equalsIgnoreCase("sun")) {
                abbrev = "Su";
            } else if (day.equalsIgnoreCase("mon")) {
                abbrev = "M";
            } else if (day.equalsIgnoreCase("tue")) {
                abbrev = "T";
            } else if (day.equalsIgnoreCase("wed")) {
                abbrev = "W";
            } else if (day.equalsIgnoreCase("thu")) {
                abbrev = "R";
            } else if (day.equalsIgnoreCase("fri")) {
                abbrev = "F";
            } else if (day.equalsIgnoreCase("sat")) {
                abbrev = "Sa";
            }
            theString = theString + "," + abbrev;
        }
        if (!theString.equals("")) {
            theString = theString.substring(1, theString.length());
        }
        return theString;
    }

    public String makeTimeString() {
        return String.format("%02d", this.hour) + ":" + String.format("%02d", this.minute);
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public int getHour() {
        return hour;
    }

    public void setHour(int hour) {
        this.hour = hour;
    }

    public int getMinute() {
        return minute;
    }

    public void setMinute(int minute) {
        this.minute = minute;
    }

    public List<String> getTimerSchedule() {
        return timerSchedule;
    }

    public void setTimerSchedule(List<String> timerSchedule) {
        this.timerSchedule = timerSchedule;
    }

    public String getFuncName() {
        return funcName;
    }

    public void setFuncName(String funcName) {
        this.funcName = funcName;
    }

    public HashMap<String, String> getArguments() {
        return arguments;
    }

    public void setArguments(HashMap<String, String> arguments) {
        this.arguments = arguments;
    }

    public boolean isEnabled() {
        return isEnabled;
    }

    public void setIsEnabled(boolean isEnabled) {
        this.isEnabled = isEnabled;
    }
}
