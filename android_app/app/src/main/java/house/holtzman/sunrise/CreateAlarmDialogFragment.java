package house.holtzman.sunrise;

import android.app.AlertDialog;

import android.app.Dialog;
import android.content.DialogInterface;
import android.os.Bundle;
import android.support.v4.app.DialogFragment;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.EditText;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.TimePicker;
import android.widget.ToggleButton;

import com.google.gson.Gson;

import java.util.ArrayList;
import java.util.List;

public class CreateAlarmDialogFragment extends DialogFragment {
    private static String TAG = "CreateAlarmDialogFragment";
    private CreateAlarmDialogListener mListener;
    private Timer timerToLoad = null;

    public interface CreateAlarmDialogListener {
        public void onDialogPositiveClick(String cmdArgs);
    }

    public CreateAlarmDialogFragment() {
        //empty required constructor
    }

    public static CreateAlarmDialogFragment newInstance(Timer timer) {
        CreateAlarmDialogFragment f = new CreateAlarmDialogFragment();
        f.timerToLoad = timer;
        return f;
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        try {
            mListener = (CreateAlarmDialogListener) getTargetFragment();
        } catch (ClassCastException e) {
            throw new ClassCastException("Calling Fragment must implement OnAddFriendListener");
        }
    }

    @Override
    public Dialog onCreateDialog(Bundle savedInstanceState) {
        // Use the Builder class for convenient dialog construction
        AlertDialog.Builder builder = new AlertDialog.Builder(getActivity());
        LayoutInflater inflater = getActivity().getLayoutInflater();
        View view = inflater.inflate(R.layout.create_alarm_dialog, null);
        ViewGroup vg = (ViewGroup) view.getParent();

        EditText etTimerId = (EditText) view.findViewById(R.id.et_timer_id);
        ToggleButton btnEnabled = (ToggleButton) view.findViewById(R.id.tb_alarm_enabled);
        ToggleButton btnSun = (ToggleButton) view.findViewById(R.id.btn_day_sun);
        ToggleButton btnMon = (ToggleButton) view.findViewById(R.id.btn_day_mon);
        ToggleButton btnTue = (ToggleButton) view.findViewById(R.id.btn_day_tue);
        ToggleButton btnWed = (ToggleButton) view.findViewById(R.id.btn_day_wed);
        ToggleButton btnThu = (ToggleButton) view.findViewById(R.id.btn_day_thu);
        ToggleButton btnFri = (ToggleButton) view.findViewById(R.id.btn_day_fri);
        ToggleButton btnSat = (ToggleButton) view.findViewById(R.id.btn_day_sat);

        final Spinner programSpinner = (Spinner) view.findViewById(R.id.spn_program_spinner);

        // Create an ArrayAdapter using the string array and a default spinner
        ArrayAdapter<CharSequence> staticAdapter2;
        staticAdapter2 = ArrayAdapter.createFromResource(getActivity(),
                R.array.programs_array,
                android.R.layout.simple_spinner_item);

        // Specify the layout to use when the list of choices appears
        staticAdapter2.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);

        // Apply the adapter to the spinner
        programSpinner.setAdapter(staticAdapter2);

        TimePicker thePicker = (TimePicker) view.findViewById(R.id.tp_alarm_time);
        thePicker.setIs24HourView(true);

        // Inflate and set the layout for the dialog
        // Pass null as the parent view because its going in the dialog layout
        builder.setView(view);
        builder.setPositiveButton("OK", new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface dialog, int id) {
                        Log.i(TAG, "clicked");
                        Dialog f = (Dialog) dialog;
                        EditText etTimerId = (EditText) f.findViewById(R.id.et_timer_id);
                        ToggleButton btnEnabled = (ToggleButton) f.findViewById(R.id.tb_alarm_enabled);
                        ToggleButton btnSun = (ToggleButton) f.findViewById(R.id.btn_day_sun);
                        ToggleButton btnMon = (ToggleButton) f.findViewById(R.id.btn_day_mon);
                        ToggleButton btnTue = (ToggleButton) f.findViewById(R.id.btn_day_tue);
                        ToggleButton btnWed = (ToggleButton) f.findViewById(R.id.btn_day_wed);
                        ToggleButton btnThu = (ToggleButton) f.findViewById(R.id.btn_day_thu);
                        ToggleButton btnFri = (ToggleButton) f.findViewById(R.id.btn_day_fri);
                        ToggleButton btnSat = (ToggleButton) f.findViewById(R.id.btn_day_sat);
                        Spinner progSpinner = (Spinner) f.findViewById(R.id.spn_program_spinner);
                        TimePicker thePicker = (TimePicker) f.findViewById(R.id.tp_alarm_time);

                        List<String> dowList = new ArrayList<>();
                        if (btnSun.isChecked()) {dowList.add("sun");}
                        if (btnMon.isChecked()) {dowList.add("mon");}
                        if (btnTue.isChecked()) {dowList.add("tue");}
                        if (btnWed.isChecked()) {dowList.add("wed");}
                        if (btnThu.isChecked()) {dowList.add("thu");}
                        if (btnFri.isChecked()) {dowList.add("fri");}
                        if (btnSat.isChecked()) {dowList.add("sat");}

                        Timer timer = new Timer(etTimerId.getText().toString(),
                                btnEnabled.isChecked(),
                                thePicker.getHour(),
                                thePicker.getMinute(),
                                dowList,
                                progSpinner.getSelectedItem().toString(),
                                null
                        );

                        Gson gson = new Gson();
                        mListener.onDialogPositiveClick(gson.toJson(timer.toJson()));

                    }
                })
                .setNegativeButton("Cancel", new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface dialog, int id) {
                        Log.i(TAG, "Cancelled dialog");
                    }
                });

        if (timerToLoad != null) {
            // editing existing timer case so prepopulate the dialog
            etTimerId.setText(timerToLoad.getId());
            btnEnabled.setChecked(timerToLoad.isEnabled());
            programSpinner.setSelection(getIndex(programSpinner, timerToLoad.getFuncName()));
            thePicker.setHour(timerToLoad.getHour());
            thePicker.setMinute(timerToLoad.getMinute());

            for (String day : timerToLoad.getTimerSchedule()) {
                if (day.equals("sun")) {
                    btnSun.setChecked(true);
                } else if (day.equals("mon")) {
                    btnMon.setChecked(true);
                } else if (day.equals("tue")) {
                    btnTue.setChecked(true);
                } else if (day.equals("wed")) {
                    btnWed.setChecked(true);
                } else if (day.equals("thu")) {
                    btnThu.setChecked(true);
                } else if (day.equals("fri")) {
                    btnFri.setChecked(true);
                } else if (day.equals("sat")) {
                    btnSat.setChecked(true);
                }
            }
        }

        builder.setMessage("Create New Timer");
        return builder.create();
    }

    //private method of your class
    private int getIndex(Spinner spinner, String myString)
    {
        int index = 0;

        for (int i=0;i<spinner.getCount();i++){
            if (spinner.getItemAtPosition(i).toString().equalsIgnoreCase(myString)){
                index = i;
                break;
            }
        }
        return index;
    }
}
