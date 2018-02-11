package house.holtzman.sunrise;

import android.content.Context;
import android.widget.Toast;

/**
 * Created by Filippo on 11/16/2015.
 */
public class Notifier {

    private CharSequence text;
    private Context context;

    public Notifier(Context context, CharSequence text) {
        this.context = context;
        this.text = text;
    }

    public void show() {
        Toast.makeText(this.context, this.text, Toast.LENGTH_LONG).show();
    }
}
