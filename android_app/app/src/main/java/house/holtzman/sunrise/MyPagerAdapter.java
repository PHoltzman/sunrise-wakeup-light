package house.holtzman.sunrise;


import android.support.v4.app.Fragment;
import android.support.v4.app.FragmentManager;
import android.support.v4.app.FragmentPagerAdapter;

/**
 * Created by Filippo on 1/20/2016.
 */
public class MyPagerAdapter extends FragmentPagerAdapter {
    static final int NUM_ITEMS = 3;

    public MyPagerAdapter(FragmentManager fm) {
        super(fm);
    }

    @Override
    public int getCount() {
        return NUM_ITEMS;
    }


    @Override
    public Fragment getItem(int position) {
        switch(position) {
            case(0):
                return TimerFragment.newInstance();
            case(1):
                return ProgramsFragment.newInstance();
            case(2):
                return AdminFragment.newInstance();
            default:
                return AdminFragment.newInstance();
        }
    }

    @Override
    public CharSequence getPageTitle(int position) {
        switch(position) {
            case(0):
                return "Alarms";
            case(1):
                return "Programs";
            case(2):
                return "Admin";
            default:
                return "Admin";
        }
    }
}
