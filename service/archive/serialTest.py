import serial
ser = serial.Serial ("/dev/ttyAMA0")    #Open named port 
ser.baudrate = 9600                     #Set baud rate to 9600
data = "1234567890"                     #Read ten characters from serial port to data
ser.write(data)                         #Send back the received data
rcvd = ser.read(10)
ser.close()
print rcvd 
