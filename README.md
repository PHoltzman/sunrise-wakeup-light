# sunrise-wakeup-light
This is a python implementation for a DIY wakeup light running on a Raspberry Pi and driving ws2811 LED pixels. It also includes an Android app for managing the alarms from a smartphone.

## Python Service
The wakeup light is a python Flask restful web service running on a Raspberry Pi 3. It supports the execution of different lighting programs, as well as the managment of alarms for automatically kicking off programs (nominally the wakeup program) at specific times during the week. The current implementation uses the SPI interface to drive a strip of ws2811 LED pixels.

## Android App
The companion Android app provides an easy way to interact with the wakeup light for managing the alarmas and executing programs.