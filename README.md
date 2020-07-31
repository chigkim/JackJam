# jackjam
Live Jam On Mac During Pandemic

*WARNING*: USE AT YOUR OWN RISK! This is in alpha cycle. Many things may not work and change frequently without notice.

JackJam is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY, expressed or implied, of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. Please see the [GNU General Public License](http://www.gnu.org/licenses/) for more details.

## Install
1. Download the following and install them.
    * [Jack2](https://jackaudio.org/downloads/)
    * [Jacktrip](https://ccrma.stanford.edu/software/jacktrip/osx/index.html)
    * JackJam: in this folder
2. In terminal, type the following to make sure everything is installed.
    * jackd --version
    * jack trip --version
3. Run the jackjam.app

Important: This is an unsigned app, so you need to bypass MacOS security. Instead of regular click to open, Right click and choose open may override the security preference. If that doesn't work, you need to dequarantine the app following the instruction below.

## Clearing the quarantine
The following instruction comes from: https://derflounder.wordpress.com/2012/11/20/clearing-the-quarantine-extended-attribute-from-downloaded-applications/

If you run the following in terminal with replacing the application path, you'll see com.apple.quarantine if your app is quarantined.

xattr /path/to/JackJam.app

In order to clear the quarantine, run the following in the terminal with replacing the path to the app.

sudo xattr -r -d com.apple.quarantine /path/to/JackJam.app

Then hopefully you can run the app with right click and choose open.

## Usage

### Server tab
* Choose your input, output, sampling rate, and buffer size
* Go to the tool bar and check start engine
* Choose Jacktrip type:
* Type the address if it's client
* In tool bar, check start JackTrip

Important:

* Hub types don't work.
* Don't trust checkbox for status whether jackd is running or jacktrip is connected. Check the console.

##  console tab
* Console don't get refresh unless you click refresh from the tool bar or switch to console tab from another tab
* Inspect commands and outputs, and make sure both jacktrip and jackd are running.
* Log is saved to /tmp/jackjam.log

### routing tab
* Choose a receiving port and a sending port
* choose connect either from tool bar or routing menu bar (ctrl+c)
* Choose a connection  and  disconnect with (ctrl+d

Important: Jacktrip:Send ports can be only connected if Jacktrip is fully connected with someone.

## Dependencies
pip install wxpython jack-client pyinstaller

## Change Log
* After  making a connection, selections in send and receive ports tables now stay
* Status for checkboxes to Start Engine and Start Jacktrip are more reliable.
* Toggle jacktrip: control+t
* Toggle engine: ctrl+e
* Display public ip address in server
* Display message when trying to connect with only one port selected.
* Logs get saved to /tmp/jackjam.log
* Connect		: ctrl+c
* Disconnect: ctrl+d

