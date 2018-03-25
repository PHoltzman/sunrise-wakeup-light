package house.holtzman.sunrise;

import android.os.Bundle;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.TextView;

import org.json.JSONException;
import org.json.JSONObject;

import java.util.Iterator;

import static android.widget.AdapterView.*;

public class ProgramsFragment extends MyFragmentTemplate {

    private static final String TAG = "ProgramsFragment";

    public ProgramsFragment() {
        // Required empty public constructor
    }

    public static ProgramsFragment newInstance() {
        return new ProgramsFragment();
    }

    @Override
    public void setUserVisibleHint(boolean isVisibleToUser) {
        super.setUserVisibleHint(isVisibleToUser);
        if (isVisibleToUser) {
            readProgram();
        }
    }

    @Override
    public View onCreateView(LayoutInflater inflater,
                             ViewGroup container,
                             Bundle savedInstanceState) {
        // Inflate the layout for this fragment
        View view = inflater.inflate(R.layout.fragment_programs, container, false);

        Button btnReadProgram = (Button) view.findViewById(R.id.btn_read_program);
        btnReadProgram.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                readProgram();
            }
        });

        Button btnBlackout = (Button) view.findViewById(R.id.btn_blackout);
        btnBlackout.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                activateProgram("blackout");
            }
        });

        Button btnSingleColor = (Button) view.findViewById(R.id.btn_single_color);
        btnSingleColor.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                TextView r, g, b;
                String red, green, blue;
                View p = (View)v.getParent();
                r = (EditText)p.findViewById(R.id.sc_1);
                g = (EditText)p.findViewById(R.id.sc_2);
                b = (EditText)p.findViewById(R.id.sc_3);

                red = r.getText().toString().trim();
                green = g.getText().toString().trim();
                blue = b.getText().toString().trim();

                JSONObject args = new JSONObject();
                try {
                    if (!red.equals("")) {
                        args.put("red", Integer.parseInt(red));
                    }
                    if (!green.equals("")) {
                        args.put("green", Integer.parseInt(green));
                    }
                    if (!blue.equals("")) {
                        args.put("blue", Integer.parseInt(blue));
                    }
                } catch (JSONException e) {
                    new Notifier(getActivity(), "Error parsing input arguments.").show();
                }

                activateProgram("single_color", args);
            }
        });

        Button btnColorChange = (Button) view.findViewById(R.id.btn_color_change);
        btnColorChange.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                View p = (View)v.getParent();
                TextView dwell = (EditText)p.findViewById(R.id.cc_1);
                TextView trans = (EditText)p.findViewById(R.id.cc_2);
                TextView scale = (EditText)p.findViewById(R.id.cc_3);

                String dwellTimeMs = dwell.getText().toString().trim();
                String transitionTimeMs = trans.getText().toString().trim();
                String scaleFactor = scale.getText().toString().trim();

                JSONObject args = new JSONObject();
                try {
                    if (!dwellTimeMs.equals("")) {
                        args.put("dwellTimeMs", Integer.parseInt(dwellTimeMs));
                    }
                    if (!transitionTimeMs.equals("")) {
                        args.put("transitionTimeMs", Integer.parseInt(transitionTimeMs));
                    }
                    if (!scaleFactor.equals("")) {
                        args.put("brightnessScalePct", Integer.parseInt(scaleFactor));
                    }
                } catch (JSONException e) {
                    new Notifier(getActivity(), "Error parsing input arguments.").show();
                }

                activateProgram("changing_color", args);
            }
        });


        Button btnWakeup = (Button) view.findViewById(R.id.btn_wakeup);
        btnWakeup.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                View p = (View)v.getParent();
                TextView mult = (EditText)p.findViewById(R.id.wakeup_1);

                String multiplier = mult.getText().toString().trim();

                JSONObject args = new JSONObject();
                try {
                    if (!multiplier.equals("")) {
                        args.put("multiplier", Integer.parseInt(multiplier));
                    }
                } catch (JSONException e) {
                    new Notifier(getActivity(), "Error parsing input arguments.").show();
                }

                activateProgram("wakeup", args);
            }
        });

        Button btnSleepy = (Button) view.findViewById(R.id.btn_sleepy);
        btnSleepy.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                View p = (View)v.getParent();
                TextView mult = (EditText)p.findViewById(R.id.sleepy_1);

                String multiplier = mult.getText().toString().trim();

                JSONObject args = new JSONObject();
                try {
                    if (!multiplier.equals("")) {
                        args.put("multiplier", Integer.parseInt(multiplier));
                    }
                } catch (JSONException e) {
                    new Notifier(getActivity(), "Error parsing input arguments.").show();
                }

                activateProgram("sleepy_time", args);
            }
        });

        return view;
    }

    public void readProgram() {
        RestClient rc = new RestClient(getContext(), getActivity());
        rc.getRequest("programs", new VolleyCallback() {
            @Override
            public void onSuccessResponse(JSONObject result) {
                String currentProgram = null;
                try {
                    currentProgram = result.get("currentProgram").toString();
                } catch (JSONException e) {
                    currentProgram = "ERROR";
                }
                TextView curProgTextView = (TextView) getView().findViewById(R.id.tv_current_program);
                curProgTextView.setText(currentProgram);
            }
        });
    }

    public void activateProgram(String program) {
        activateProgram(program, null);
    }

    public void activateProgram(String program, JSONObject args) {
        String argStr = "";
        Log.i(TAG, String.format("Activating %s program", program));
        if (args != null) {
            Log.i(TAG, String.format("Arguments: %s", args.toString()));
            argStr = argStr + "?";

            try {
                Iterator<?> keys = args.keys();
                while (keys.hasNext()) {
                    String key = (String) keys.next();
                    argStr = argStr + key + "=" + args.get(key).toString() + "&";
                }
                argStr = argStr.substring(0, argStr.length() -1);

            } catch (JSONException e) {
                Log.e(TAG, e.getMessage());
                new Notifier(getActivity(), "Error mapping input arguments when sending request.").show();
                return;
            }
        }
        RestClient rc = new RestClient(getContext(), getActivity());
        rc.getRequest("programs/" + program + argStr, new VolleyCallback() {
            @Override
            public void onSuccessResponse(JSONObject result) {
                readProgram();
            }
        });
    }
}
