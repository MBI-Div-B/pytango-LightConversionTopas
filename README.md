# pytango-LightConversionTopas
PyTango Device Server for Light Conversion OPAs

# Requirements
The OPA needs to be controlled by WinTopas4 (http://topas4info.lightcon.com/?utm_source=Topas4APIPage). Communication between the pytango device server and WinTopas4 is established through TCP/IP. The device can be connected to the computer running the pytango device server or to a remote computer on the same network. The PyTango device server is compatible with any OPA controlled by WinTopas4 (TOPAS, ORPHEUS).

# Device properties
IP - IP address of the computer controlling the OPA; enter 127.0.0.1 if the OPA is local.

port - communication port; typically in the range of 8000-8006; correct port is displayed by WinTopas4 Server Application (version >1.148.20)

serial - serial number of the OPA; five-digit number.

# Attributes
wavelength: read/write output wavelength (float)

energy: read/write output photon energy (float)

ShutterOpen: read/write shutter position (boolean, True = open, False = closed)

authentication: read (boolean; for remote OPAs, only authenticated computers can change OPA settings including output wavelength and shutter position)

interactions: read (string; lists all available interactions and corresponding wavelength ranges)
