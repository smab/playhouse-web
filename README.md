Playhouse-Web server
====================

This is the server that serves templates and communicates with the lamp 
server in the playhouse project.  


Quick links
-----------

* `Source (github) <https://github.com/smab/playhouse-web>`



Setup
-----

To run the server you must first install the python library tornado, which
can be found at <http://tornadoweb.org>. Additional installs might include
the python3 library and pip.

Then, located in the playhouse-web root folder, issue the following commands:

      python3 src/dummyserver.py
      python3 src/webserver.py

It is advisable to run the two commands in separate terminal windows to 
distinguish the different output from the two servers.
The dummyserver is a local lampserver that simulates the control of the 
hue-lights. The webserver runs the front-end as well as the config for the 
front-end.
To access the config interface, go to <http://localhost:8081/config>,
whereas the address <http://localhost:8080/> displays the actual animations/
games.
To change the startup behaviour of the webserver, edit the config.json file
in the root directory.
If you wish to add password protection to the config interface you can add
the parameter "config_pwd" followed by a password string. This will be
stored in plaintext and should not be considered safe by any means. 
The default username to log in using the password is "admin".
