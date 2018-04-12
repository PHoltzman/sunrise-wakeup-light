# sunrise-wakeup-light
This is a python implementation for a DIY wakeup light running on a Raspberry Pi and driving ws2811 LED pixels. It also includes an Android app for managing the alarms from a smartphone.

If you run into issues, please contact me and I will do my best to help.

## Known Issues
 - There is currently an issue with stopping the python service using systemd stop. This is due to gunicorn intercepting the sigterm or sigint (not sure which) message and not flowing it through to the service. The service is wanting to receive that itself so it can clean up the thread it spawned for driving the LEDs. The outcome is that the service hangs during stop and sometimes a rogue thread is left hanging out there.

## Components
### Python Service
The wakeup light is a python Flask restful web service running on a Raspberry Pi 3. It supports the execution of different lighting programs, as well as the management of alarms for automatically kicking off programs (nominally the wakeup program) at specific times during the week. The current implementation uses the SPI interface to drive a strip of ws2811 LED pixels.

#### Hardware
There is a folder with pictures of the hardware setup and a schematic of the wiring.

### Android App
The companion Android app provides an easy way to interact with the wakeup light for managing the alarms and executing programs. The only setup for the app after installing is to go to the admin tab, click on settings, and enter the IP address and port at which the python service is running.


## Programs
Here are short summaries of the currently implemented lighting programs. Also included in the repo are a few example videos showing a few of the programs running.

### Wakeup
This is the wakeup program that runs a sunrise sequence and is the reason I built this in the first place. A 'multiplier' parameter allows for control of the overall runtime with 30 being the default value for a roughly 30 minute wakeup sequence. The video shows the 1 minute version.

### Color Change
This program shifts randomly between about 15 nice looking colors. This program accepts parameters to change the dwell time (length of time spent on each color), transition time (the length of time spent actively changing from one color to the next), and brightness percentage (percentage from 0 to 100 by which the light values are scaled). The video is at the default of 10000 milliseconds dwell, 3000 milliseconds transition, and 100% brightness. 30% brightness seems to be a nice level while laying in bed before sleep, at least at my house.

### Single Color
This program sets the lights to a specific single color. The color is specified with red, green, and blue values from 0 (off) to 255 (full on).

### Sleepy Time
This program starts with the leds on with a red color at half brightness (128 value) and slowly transitions them to off. It is nice when going to sleep to have a bit of soft light for last minute tasks with a nice smooth fade out. It accepts a multiplier parameter (just like the wakeup program) and the default value is 5 for a roughly five minute fade out. The video uses a value of 1.

### Blackout
This program turns off all the leds and is running whenever another program is not. In an earlier iteration, I did not have this running all the time and occasionally some static shocks or other transient event would cause a few LEDs to turn on even though they weren't being commanded. By always commanding to black, any transient events are immediately corrected.


## Alarms
Alarms serve to kick off a program to run at a specified time. The interface should be self explanatory. I normally only ever use this functionality with the wakeup program and set it to run 30 minutes before the time my alarm clock will go off. In theory, this allows the body to wakeup naturally with the increasing light such that you are already mostly awake when the alarm clock sounds.


