import rpi_ws281x

import time

# LED strip configuration:
LED_COUNT      = 50      # Number of LED pixels.
#LED_PIN        = 12      # GPIO pin connected to the pixels (18 uses PWM!).
LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 5       # DMA channel to use for generating signal (try 5)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
#LED_STRIP      = ws.WS2811_STRIP_GRB   # Strip type and colour ordering


def colorWipe(strip, color, wait_ms=50):
	"""Wipe color across display a pixel at a time."""
	for i in range(strip.numPixels()):
		strip.setPixelColor(i, color)
		strip.show()
		time.sleep(wait_ms/1000.0)

# Main program logic follows:
if __name__ == '__main__':
	# Create NeoPixel object with appropriate configuration.
	strip = rpi_ws281x.PixelStrip(LED_COUNT, LED_PIN)
	# Intialize the library (must be called once before other functions).
	strip.begin()

	print ('Press Ctrl-C to quit.')
	while True:
		print ('Color wipe animations.')
		colorWipe(strip, rpi_ws281x.Color(255, 0, 0))  # Red wipe
		colorWipe(strip, rpi_ws281x.Color(0, 255, 0))  # Blue wipe
		colorWipe(strip, rpi_ws281x.Color(0, 0, 255))  # Green wipe
		colorWipe(strip, rpi_ws281x.Color(255, 255, 255))  # White wipe
