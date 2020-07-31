from urllib.request import urlopen
from datetime import datetime
import sys
import wx
import os
import json
import argparse
from time import sleep
import subprocess
import re
import jack
import select
from threading import Thread, Event, Lock
from queue import Queue

def log(line):
	with lock:
		q.put(line)
		f.write(line+'\n')
		f.flush()

def process(cmd, e):
	log(f'Command: {cmd}')
	if 'jacktrip' in cmd:
		frame.serverPanel.connectCheckBox.SetValue(True)
	elif 'jackd' in cmd:
		frame.serverPanel.startCheckBox.SetValue(True)
	proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
	poll = select.poll()
	poll.register(proc.stdout, select.POLLIN)
	while e.is_set():
		if poll.poll(0):
			line = proc.stdout.readline().decode('utf-8')
			if line == '': break
			log(line[:-1])
	proc.stdin.close()
	proc.kill()
	log(f'Killed {cmd}')
	e.clear()
	if 'jacktrip' in cmd:
		frame.serverPanel.connectCheckBox.SetValue(False)
	elif 'jackd' in cmd:
		frame.serverPanel.startCheckBox.SetValue(False)

class RunWhile():
	def __init__(self):
		self.e = Event()
		self.t = None

	def start(self, cmd):
		self.e.set()
		self.t = Thread(target=process, args=(cmd, self.e))
		self.t.start()

	def stop(self):
		if self.t:
			self.e.clear()
			self.t.join()

	def is_alive(self):
		return self.e.is_set()

class RoutingPanel(wx.Panel):
	def __init__(self, parent):
		self.connections = []
		wx.Panel.__init__(self, parent)
		grid = wx.GridSizer(cols=3, gap=(5,5))

		label = wx.StaticText(self, label='Receive')
		grid.Add(label)
		label = wx.StaticText(self, label='Send')
		grid.Add(label)
		label = wx.StaticText(self, label='Connection')
		grid.Add(label)
		self.receiveList = wx.ListBox(self)
		grid.Add(self.receiveList)
		self.sendList = wx.ListBox(self)
		grid.Add(self.sendList)

		self.connectionList = wx.ListBox(self)
		grid.Add(self.connectionList)

		grid.SetSizeHints(self)
		self.SetSizerAndFit(grid)
		self.client = None
		self.SetAutoLayout(True)

	def setToolBar(self, tb):
		tb.ClearTools()
		refreshButton = wx.Button(tb, label='Refresh')
		tb.GetParent().Bind(wx.EVT_BUTTON, self.refresh, refreshButton)
		tb.AddControl(refreshButton).SetShortHelp('Refresh')
		connectButton = wx.Button(tb, label='Connect')
		tb.GetParent().Bind(wx.EVT_BUTTON, self.connect, connectButton)
		tb.AddControl(connectButton).SetShortHelp('Connect')
		disconnectButton = wx.Button(tb, label='Disconnect')
		tb.GetParent().Bind(wx.EVT_BUTTON, self.disconnect, disconnectButton)
		tb.AddControl(disconnectButton).SetShortHelp('Disconnect')
		tb.Realize()
		self.refresh()

	def refresh(self, e=None):
		if jackd.is_alive() and self.client == None:
			log('Opening Client')
			self.client = jack.Client('Jack Jam')
		if jackd.is_alive() == False or self.client == None:
			self.receiveChoices = []
			self.sendChoices =[]
		else:
			self.receiveChoices = [c.name for c in self.client.get_ports(is_output=True)]
			self.sendChoices = [c.name for c in self.client.get_ports(is_input=True)]
		self.receiveList.Set(self.receiveChoices)
		self.sendList.Set(self.sendChoices)
		self.refreshConnections()

	def refreshConnections(self):
		self.connections = []
		for port in self.receiveChoices:
			connectedPorts = self.client.get_all_connections(port)
			for connectedPort in connectedPorts:
				self.connections.append(port+' -> '+connectedPort.name)
		self.connectionList.Set(self.connections)
		self.Layout()

	def connect(self, e):
		r = self.receiveList.GetSelection()
		s = self.sendList.GetSelection()
		if r<0 or s<0:
			wx.MessageBox('Please select both receive and send ports to connect.')
		else:
			p1 = self.receiveList.GetString(r)
			p2 = self.sendList.GetString(s)
			self.client.connect(p1, p2)
			self.refreshConnections()
			c = f'{p1} -> {p2}'
			c = self.connections.index(c)
			self.connectionList.SetSelection(c)
			self.connectionList.EnsureVisible(c)

	def disconnect(self, e):
		c = self.connectionList.GetSelection()
		if c<0:
			wx.MessageBox('Please select a connection to disconnect.')
		else:
			connection = self.connectionList.GetString(c).split(' -> ')
			p1 = connection[0]
			p2 = connection[1]
			self.client.disconnect(p1, p2)
			self.refreshConnections()

class ServerPanel(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent)
		self.started = False
		self.connected = False
		grid = wx.GridSizer(cols=4, gap=(5,5))

		label = wx.StaticText(self, label='Input')
		grid.Add(label)
		choices = [d['name'] for d in devices]
		self.inputChoice = wx.Choice(self, choices=choices)
		grid.Add(self.inputChoice)

		label = wx.StaticText(self, label='Output')
		grid.Add(label)
		self.outputChoice = wx.Choice(self, choices=choices)
		grid.Add(self.outputChoice)

		label = wx.StaticText(self, label='Sample Rate')
		grid.Add(label)
		self.rates = ['22050', '44100', '48000']
		self.rateChoice = wx.Choice(self, choices=self.rates, name='Sample Rate')
		self.rateChoice.SetStringSelection('44100')
		grid.Add(self.rateChoice)

		label = wx.StaticText(self, label='Buffer Size')
		grid.Add(label)
		self.bufs = ['32', '64', '128', '256', '512', '1024']
		self.bufChoice = wx.Choice(self, choices=self.bufs, name='Sample Rate')
		self.bufChoice.SetStringSelection('128')
		grid.Add(self.bufChoice)

		label = wx.StaticText(self, label='Type')
		grid.Add(label)
		self.types = ['Client', 'Hub Client', 'Server', 'Hub Server']
		self.typeChoice = wx.Choice(self, choices=self.types, name='Type')
		self.typeChoice.SetStringSelection(self.types[0])
		grid.Add(self.typeChoice)

		label = wx.StaticText(self, label='Address')
		grid.Add(label)
		self.address = wx.TextCtrl(self)
		grid.Add(self.address)

		label = wx.StaticText(self, label='Your Public IP')
		grid.Add(label)
		try:
			external_ip = urlopen('http://checkip.amazonaws.com').read().decode('utf-8').strip()
		except:
			external_ip = 'Unable to retrieve'
		label = wx.StaticText(self, label=external_ip)
		grid.Add(label)
		grid.SetSizeHints(self)
		self.SetSizerAndFit(grid)
		self.SetAutoLayout(True)

	def setToolBar(self, tb):
		tb.ClearTools()
		self.startCheckBox = wx.CheckBox(tb, label='Start Engine')
		self.startCheckBox.SetValue(jackd.is_alive())
		tb.GetParent().Bind(wx.EVT_CHECKBOX, self.toggleEngine, self.startCheckBox)
		tb.AddControl(self.startCheckBox)
		self.connectCheckBox = wx.CheckBox(tb, label='Start JackTrip')
		self.connectCheckBox.SetValue(jacktrip.is_alive())
		tb.GetParent().Bind(wx.EVT_CHECKBOX, self.toggleTrip, self.connectCheckBox)
		tb.AddControl(self.connectCheckBox)
		tb.Realize()

	def toggleEngine(self, e):
		if jackd.is_alive():
			stop()
		else:
			start()


	def toggleTrip(self, e):
		if jacktrip.is_alive():
			disconnect()
		else:
			connect()

class ConsolePanel(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent)
		self.log = wx.TextCtrl(self, style=wx.TE_MULTILINE)
		sizer = wx.BoxSizer()
		sizer.Add(self.log, 1, wx.EXPAND)
		sizer.SetSizeHints(self)
		self.SetSizerAndFit(sizer)
		self.SetAutoLayout(True)

	def setToolBar(self, tb):
		tb.ClearTools()
		refreshButton = wx.Button(tb, label='Refresh')
		tb.GetParent().Bind(wx.EVT_BUTTON, self.refresh, refreshButton)
		tb.AddControl(refreshButton).SetShortHelp('Refresh')
		tb.Realize()
		self.refresh()

	def refresh(self, e=None):
		while not q.empty():
			line = q.get()
			self.log.AppendText(line+'\n')
		self.Layout()

class Window(wx.Frame):
	def __init__(self, parent, title):
		wx.Frame.__init__(self, parent, title=title)
		self.dirname=""
		self.filename=""
		self.CreateStatusBar()
		fileMenu= wx.Menu()
		newMenu = fileMenu.Append(wx.ID_NEW)
		self.Bind(wx.EVT_MENU, self.onNew, newMenu)
		openMenu = fileMenu.Append(wx.ID_OPEN)
		self.Bind(wx.EVT_MENU, self.onOpen, openMenu)
		saveMenu = fileMenu.Append(wx.ID_SAVE)
		self.Bind(wx.EVT_MENU, self.onSave, saveMenu)
		saveAsMenu = fileMenu.Append(wx.ID_SAVEAS)
		self.Bind(wx.EVT_MENU, self.onSaveAs, saveAsMenu)
		exitMenu = fileMenu.Append(wx.ID_EXIT)
		self.Bind(wx.EVT_MENU, self.OnExit, exitMenu)
		menuBar = wx.MenuBar()
		menuBar.Append(fileMenu,"&File")
		self.nb = wx.Notebook(self)
		self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnNotebookChanged, self.nb)

		self.serverPanel = ServerPanel(self.nb)
		self.nb.AddPage(self.serverPanel, "Server")
		self.routingPanel = RoutingPanel(self.nb)
		self.nb.AddPage(self.routingPanel, "Routing")
		self.consolePanel = ConsolePanel(self.nb)
		self.nb.AddPage(self.consolePanel, "Console")

		viewMenu= wx.Menu()
		serverViewMenu = viewMenu.Append(wx.ID_ANY, "&Server\tCTRL+1")
		self.Bind(wx.EVT_MENU, self.onViewServer, serverViewMenu)
		routingViewMenu = viewMenu.Append(wx.ID_ANY, "&Routing\tCTRL+2")
		self.Bind(wx.EVT_MENU, self.onViewRouting, routingViewMenu)
		consoleViewMenu = viewMenu.Append(wx.ID_ANY, "&Console\tCTRL+3")
		self.Bind(wx.EVT_MENU, self.onViewConsole, consoleViewMenu)
		menuBar.Append(viewMenu,"&View")

		serverMenu= wx.Menu()
		toggleEngineMenu = serverMenu.Append(wx.ID_ANY, '&Toggle Engine\tRAWCTRL-e')
		self.Bind(wx.EVT_MENU, self.serverPanel.toggleEngine, toggleEngineMenu)
		toggleTripMenu = serverMenu.Append(wx.ID_ANY, 'Toggle Jack&Trip\tRAWCTRL-t')
		self.Bind(wx.EVT_MENU, self.serverPanel.toggleTrip, toggleTripMenu)
		menuBar.Append(serverMenu,"&Server")		

		routingMenu= wx.Menu()
		refreshMenu = routingMenu.Append(wx.ID_ANY, '&Refresh\tCTRL-R')
		self.Bind(wx.EVT_MENU, self.routingPanel.refresh, refreshMenu)
		connectMenu = routingMenu.Append(wx.ID_ANY, '&Connect\tRAWCTRL-C')
		self.Bind(wx.EVT_MENU, self.routingPanel.connect, connectMenu)
		disconnectMenu = routingMenu.Append(wx.ID_ANY, '&Disconnect\tRAWCTRL-D')
		self.Bind(wx.EVT_MENU, self.routingPanel.disconnect, disconnectMenu)
		menuBar.Append(routingMenu,"&Routing")		

		self.SetMenuBar(menuBar)

		sizer = wx.BoxSizer()
		sizer.Add(self.nb, 1, wx.EXPAND)
		sizer.SetSizeHints(self)
		self.SetSizerAndFit(sizer)

		self.tb = wx.ToolBar(self, style=wx.TB_TEXT)
		self.ToolBar = self.tb
		self.serverPanel.setToolBar(self.tb)
		self.SetAutoLayout(True)
		self.Show(True)
		#self.Maximize(True)
		self.SetTitle("Jack Jam")
		self.Bind(wx.EVT_CLOSE, self.onClose, self)

	def onViewServer(self, e):
		self.nb.SetSelection(0)

	def onViewRouting(self, e):
		self.nb.SetSelection(1)

	def onViewConsole(self, e):
		self.nb.SetSelection(2)


	def OnNotebookChanged(self, e):
		if e.GetSelection() == 0:
			self.serverPanel.setToolBar(self.tb)
		if e.GetSelection() == 1:
			self.routingPanel.setToolBar(self.tb)
		if e.GetSelection() == 2:
			self.consolePanel.setToolBar(self.tb)


		'''
		focus = None
		if e.GetSelection() == 0:
			focus = self.mdPanel.control
		else:
			focus =self.WebPanel.browser
		self.focus(focus)
		'''

	def onOpen(self,e):			
		log('open')

	def onNew(self, e):
		log('new')

	def onSave(self, e):
		log('save')
	def onSaveAs(self, e):
		log('save as')

	def OnExit(self,e):
		self.Close(True)

	def onClose(self, event):
		stop()
		self.Destroy()

def run_command(cmd):
	log(f'Command: {cmd}')
	proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
	out = proc.stdout.decode('utf-8')
	log(out)
	err = proc.stderr.decode('utf-8')
	log(err)
	return out

def list_devices():
	cmd = '/usr/local/bin/jackd -d coreaudio -l'
	outs = run_command(cmd)
	regex = r"Device ID = '(.*?)' name = '(.*?)', internal name = '(.*?)'"
	i = 0

	devices = []
	for device in re.finditer(regex, outs):
		log(f'{i}, {device.group(2)}, {device.group(3)}')
		device = {'name': device.group(2), 'id':"'"+device.group(3)+"'"}
		devices.append(device)
		i += 1
	return devices
		
	
def save(settingss, file = 'jack.json'):
	with open(file, 'w') as f:
		f.write(json.dumps(settings))

def start():
	in_device = devices[frame.serverPanel.inputChoice.GetSelection()]['id']
	out_device = devices[frame.serverPanel.outputChoice.GetSelection()]['id']
	rate = frame.serverPanel.rates[frame.serverPanel.rateChoice.GetSelection()]
	buf = frame.serverPanel.bufs[frame.serverPanel.bufChoice.GetSelection()]
	cmd = f'/usr/local/bin/jackd -d coreaudio -r {rate} -p {buf} -C {in_device} -P {out_device}'
	jackd.start(cmd)

def stop():
	if frame.routingPanel.client != None:
		frame.routingPanel.client.close()
		frame.routingPanel.client = None
	if jacktrip.is_alive(): jacktrip.stop()
	if jackd.is_alive():
		jackd.stop()
		if frame.serverPanel.connectCheckBox: frame.serverPanel.connectCheckBox.SetValue(False)
		frame.serverPanel.connected = False

def connect():
	type = frame.serverPanel.types[frame.serverPanel.typeChoice.GetSelection()]
	if type == 'Client':
		cmd = '/usr/local/bin/jacktrip -c '+frame.serverPanel.address.GetValue()
	elif type == 'Hub Client':
		cmd = '/usr/local/bin/jacktrip -C '+frame.serverPanel.address.GetValue()
	elif type == 'Server':
		cmd = '/usr/local/bin/jacktrip -s'
	elif type == 'Hub Server':
		cmd = '/usr/local/bin/jacktrip -S'
	jacktrip.start(cmd)

def disconnect():
	if jacktrip.is_alive: jacktrip.stop()
	if frame.serverPanel.connectCheckBox: frame.serverPanel.connectCheckBox.SetValue(False)
	frame.serverPanel.connected = False

def get_Path():
	if getattr(sys, 'frozen', False) :
		path = os.path.abspath(sys.executable)
	else:
		path = os.path.abspath(__file__)
	return path

if __name__ == '__main__':
	q = Queue()
	lock = Lock()
	f = open('/tmp/jackjam.log', 'w')
	frame = None
	log('App Starting')
	log(str(datetime.now()))
	log(get_Path())
	outs = run_command('pkill jacktrip')
	outs = run_command('pkill jackd')
	devices = list_devices()
	client = None
	jackd = RunWhile()
	jacktrip = RunWhile()
	app = wx.App(False)
	frame = Window(None, title="Jack Jam")
	#frame.SetInitialSize(wx.Size(1000,500))
	app.MainLoop()


	'''
	if args.load: settings = json.load(open(args.load, 'r'))
	elif args.save: settings = manual(args.save)
	else:
		if os.path.exists('jack.json'):
			settings = json.load(open('jack.json', 'r'))
		else: settings = manual()
	sr = settings['sr']
	buf = settings['buf']
	in_device=settings['in_device']
	out_device = settings['out_device']
	ip = settings['ip']
	'''