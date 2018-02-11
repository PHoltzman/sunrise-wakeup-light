package house.holtzman.sunrise;

import android.app.AlertDialog;
import android.content.DialogInterface;
import android.os.Bundle;
import android.text.TextUtils;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.CompoundButton;
import android.widget.ImageButton;
import android.widget.LinearLayout;
import android.widget.TableRow;
import android.widget.TextView;
import android.widget.ToggleButton;

import com.google.gson.Gson;

import org.json.JSONException;
import org.json.JSONObject;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;

import java.util.Iterator;
import java.util.List;


public class TimerFragment extends MyFragmentTemplate implements CreateAlarmDialogFragment.CreateAlarmDialogListener {

    private static final String TAG = "TimerFragment";

    public TimerFragment() {
        // Required empty public constructor
    }

    /**
     * Use this factory method to create a new instance of
     * this fragment using the provided parameters.
     *
     * @return A new instance of fragment TimerFragment.
     */
    public static TimerFragment newInstance() {
        return new TimerFragment();
    }


    @Override
    public View onCreateView(LayoutInflater inflater,
                             ViewGroup container,
                             Bundle savedInstanceState) {
        // Inflate the layout for this fragment
        View view = inflater.inflate(R.layout.fragment_timer, container, false);

        Button btnReadAlarms = (Button) view.findViewById(R.id.btn_read_alarms);
        btnReadAlarms.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                getTimers();
            }
        });

        Button btnNewAlarm = (Button) view.findViewById(R.id.btn_new_alarm);
        btnNewAlarm.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                createAlarm();
            }
        });

        return view;
    }

    @Override
    public void setUserVisibleHint(boolean isVisibleToUser) {
        super.setUserVisibleHint(isVisibleToUser);
        if (isVisibleToUser) {
            getTimers();
        }
    }

    public void renderTimers(JSONObject response) {
        Timer timer;
        TextView tvTimerId, tvAlarmsStatus, tvAlarmDay, tvAlarmTime, tvAlarmProgram;
        ImageButton btnEdit, btnDelete;
        ToggleButton alarmToggle;
        TableRow rowLayout, row2Layout;

        // setup the table for displaying the current alarms
        TableRow.LayoutParams params = new TableRow.LayoutParams(
                TableRow.LayoutParams.WRAP_CONTENT,
                TableRow.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(30, 30, 10, 10);

        TableRow.LayoutParams toggleParams = new TableRow.LayoutParams(
                200,
                125
        );
        toggleParams.setMargins(30, 30, 10, 10);

        TableRow.LayoutParams editBtnParams = new TableRow.LayoutParams(
                125,
                125
        );
        TableRow.LayoutParams delBtnParams = new TableRow.LayoutParams(
                125,
                125
        );
        editBtnParams.setMargins(30, 30, 10, 10);
        delBtnParams.setMargins(30, 30, 10, 10);

        LinearLayout curAlarmsLayout = (LinearLayout) getView().findViewById(R.id.lyt_current_alarms);
        if (curAlarmsLayout.getChildCount() > 0) {
            curAlarmsLayout.removeAllViews();
        }

        tvAlarmsStatus = (TextView) getView().findViewById(R.id.tv_alarms_status);

        // iterate through items in response object and render them
        try {
            JSONObject timers = response.getJSONObject("timers");
            Iterator<?> keys = timers.keys();
            boolean foundAny = false;
            while (keys.hasNext()) {
                foundAny = true;
                String key = (String) keys.next();

                timer = new Timer((JSONObject) timers.get(key));

                rowLayout = new TableRow(getActivity());
                row2Layout = new TableRow(getActivity());
                rowLayout.setTag(timer);
                row2Layout.setTag(timer);

                tvTimerId = new TextView(getActivity());
                tvTimerId.setText(timer.getId());
                tvTimerId.setLayoutParams(params);
                rowLayout.addView(tvTimerId);

                tvAlarmDay = new TextView(getActivity());
                tvAlarmDay.setText(timer.makeTimerScheduleString());
                tvAlarmDay.setLayoutParams(params);
                rowLayout.addView(tvAlarmDay);

                tvAlarmTime = new TextView(getActivity());
                tvAlarmTime.setText(timer.makeTimeString());
                tvAlarmTime.setLayoutParams(params);
                rowLayout.addView(tvAlarmTime);

                tvAlarmProgram = new TextView(getActivity());
                tvAlarmProgram.setText(timer.getFuncName());
                tvAlarmProgram.setLayoutParams(params);
                rowLayout.addView(tvAlarmProgram);

                alarmToggle = new ToggleButton(getActivity());
                alarmToggle.setMinWidth(0);
                alarmToggle.setChecked(timer.isEnabled());
                alarmToggle.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
                    public void onCheckedChanged(CompoundButton v, boolean isChecked) {
                        ViewGroup parent = (ViewGroup) v.getParent();
                        Timer timer = (Timer) parent.getTag();
                        if (isChecked) {
                            enableTimer(timer);
                        } else {
                            disableTimer(timer);
                        }
                    }
                });
                alarmToggle.setLayoutParams(toggleParams);
                row2Layout.addView(alarmToggle);

                btnEdit = new ImageButton(getActivity());
                btnEdit.setImageResource(R.drawable.ic_menu_edit);
                btnEdit.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        ViewGroup parent = (ViewGroup) v.getParent();
                        editTimer((Timer) parent.getTag());
                    }
                });
                row2Layout.addView(btnEdit);
                btnEdit.setLayoutParams(editBtnParams);

                btnDelete = new ImageButton(getActivity());
                btnDelete.setImageResource(R.drawable.ic_menu_delete);
                btnDelete.setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View v) {
                        ViewGroup parent = (ViewGroup) v.getParent();
                        deleteTimer((Timer) parent.getTag());
                    }
                });
                row2Layout.addView(btnDelete);
                btnDelete.setLayoutParams(delBtnParams);

                curAlarmsLayout.addView(rowLayout);
                curAlarmsLayout.addView(row2Layout);

            }
            if (!foundAny) {
                tvAlarmsStatus.setText("No Timers Set");
                tvAlarmsStatus.setVisibility(TextView.VISIBLE);
            } else {
                tvAlarmsStatus.setVisibility(TextView.INVISIBLE);
            }

        } catch (JSONException e) {
            Log.i(TAG, e.getMessage());
            new Notifier(getActivity(), "Error processing JSON response.").show();
        }
    }

    public void getTimers() {
        RestClient rc = new RestClient(getContext(), getActivity());
        rc.getRequest("timers", new VolleyCallback() {
            @Override
            public void onSuccessResponse(JSONObject result) {
                Log.i(TAG, result.toString());
                renderTimers(result);
            }
        });
    }

    public void enableTimer(Timer timer) {
        RestClient rc = new RestClient(getContext(), getActivity());
        rc.getRequest("timers/" + timer.getId() + "/enable", new VolleyCallback() {
            @Override
            public void onSuccessResponse(JSONObject result) {
                getTimers();
            }
        });
    }

    public void disableTimer(Timer timer) {
        RestClient rc = new RestClient(getContext(), getActivity());
        rc.getRequest("timers/" + timer.getId() + "/disable", new VolleyCallback() {
            @Override
            public void onSuccessResponse(JSONObject result) {
                getTimers();
            }
        });
    }

    public void deleteTimer(Timer timer) {
        RestClient rc = new RestClient(getContext(), getActivity());
        rc.deleteRequest("timers/" + timer.getId(), new VolleyCallback() {
            @Override
            public void onSuccessResponse(JSONObject result) {
                getTimers();
            }
        });
    }

    public void editTimer(Timer timer) {
        CreateAlarmDialogFragment dialog = CreateAlarmDialogFragment.newInstance(timer);
        dialog.setTargetFragment(this,0);

        dialog.show(getFragmentManager(), "createAlarm");
    }

    public void createAlarm() {
        CreateAlarmDialogFragment dialog = CreateAlarmDialogFragment.newInstance(null);
        dialog.setTargetFragment(this,0);
        dialog.show(getFragmentManager(), "createAlarm");
    }

    @Override
    public void onDialogPositiveClick(String jsonString) {
//        new Notifier(getActivity(), "Creating/editing alarm. Please wait...").show();
        Log.i(TAG, jsonString);
        RestClient rc = new RestClient(getContext(), getActivity());
        JSONParser parser = new JSONParser();
        try {
            JSONObject postBody = new JSONObject(jsonString);
            rc.postRequest("timers", postBody,  new VolleyCallback() {
                @Override
                public void onSuccessResponse(JSONObject result) {
                    getTimers();
                }
            });
        } catch (JSONException e) {
            Log.e(TAG, e.getMessage());
            new Notifier(getActivity(), "Error processing timer").show();
        }

    }
}
