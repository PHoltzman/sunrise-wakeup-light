package house.holtzman.sunrise;

import android.content.Intent;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;
import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;


public class AdminFragment extends MyFragmentTemplate {

    private static final String TAG = "AdminFragment";

    /**
     * Use this factory method to create a new instance of
     * this fragment using the provided parameters.
     *
     * @return A new instance of fragment AdminFragment.
     */
    public static AdminFragment newInstance() {
        return new AdminFragment();
    }

    public AdminFragment() {
        // Required empty public constructor
    }

    @Override
    public View onCreateView(LayoutInflater inflater,
                             ViewGroup container,
                             Bundle savedInstanceState) {
        // Inflate the layout for this fragment
        View view = inflater.inflate(R.layout.fragment_admin, container, false);

        Button btnReadtime = (Button) view.findViewById(R.id.btn_read_time);
        btnReadtime.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                getCurrentTime();
            }
        });

        Button btnSettings = (Button) view.findViewById(R.id.btn_launch_settings);
        btnSettings.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                launchSettings();
            }
        });

        return view;
    }

    @Override
    public void setUserVisibleHint(boolean isVisibleToUser) {
        super.setUserVisibleHint(isVisibleToUser);
        if (isVisibleToUser) {
            getCurrentTime();
        }
    }

    public void getCurrentTime() {
        RestClient rc = new RestClient(getContext(), getActivity());
        Log.i(TAG, "Requesting current time from server");
        rc.getRequest("time", new VolleyCallback() {
            @Override
            public void onSuccessResponse(JSONObject result) {
                String currentTime = null;
                try {
                    currentTime = result.get("currentTime").toString();
                } catch (JSONException e) {
                    currentTime = "ERROR";
                }
                TextView curTimeTextView = (TextView) getView().findViewById(R.id.tv_current_time);
                curTimeTextView.setText(currentTime);
            }
        });
    }

    public void launchSettings() {
        Intent i = new Intent(getActivity(), PrefsActivity.class);
        startActivity(i);
    }

}
