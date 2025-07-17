#!/usr/bin/env python3

# Maybe someday...
# 1 - Handle docker compose logs being passed in
#     Eh, when I look at the output locally, it's flooded with pact-stub-server stuff of dubious value...
# 2 - Alert that upstream might be buffering (ie, grep without --line-buffered)

# Requires Python 3.9 or newer... some combination of tksheet (3.8) and ET.indent (3.9) drive that requirement, I think...

from json import dumps, loads
from tksheet import Sheet  # pip install tksheet
import re
import subprocess
import sys
import threading
from time import sleep, time
import traceback
import tkinter as tk
import xml.etree.ElementTree as ET

inputs = []

def dockerPs():
    # Returns a mapping of container id -> image name
    psOutLines = subprocess.check_output(['docker', 'ps'], text=True).split('\n')[1:-1]
    return {line.split()[0]: line.split()[1].split('/')[1].split(':')[0] for line in psOutLines}

def selectBestDockerContainer():
    containers = dockerPs()
    # So... now we want to run check_output on each of them... and we want the one with the most lines of json.
    bestSoFar = list(containers.keys())[0]
    bestLinesSoFar = 0
    for container in containers.keys():
        # Figure out limiting the output here...
        linesOfJson = sum(line.startswith('{') and line.endswith('}') for line in subprocess.check_output(['docker', 'logs', '--tail', '1000', container], text=True, stderr=subprocess.STDOUT).split('\n'))
        if linesOfJson > bestLinesSoFar:
            bestLinesSoFar = linesOfJson
            bestSoFar = container
    return bestSoFar

if not sys.stdin.isatty():
    inputs.append(sys.stdin)
else:
    container = selectBestDockerContainer()
    inputs.append(subprocess.Popen(['docker', 'logs', container, '--follow'], stdout=subprocess.PIPE, text=True, stderr=subprocess.STDOUT).stdout)

def clickOnRow(event):
    if hasattr(event['selected'], 'row'):
        row = event['selected'].row
        selectRow(row)

def addLinebreaks(s):
    if isinstance(s, dict) or isinstance(s, list):
        return dumps(s, indent=4)

    if not isinstance(s, str) or len(s) < 100 or '\n' in s:
        return s

    try:
      if s.startswith('<'):
        # 1 - Attempt to format as XML
        loaded = ET.XML(s)
        ET.indent(loaded)
        return ET.tostring(loaded, encoding='unicode')
      elif s.startswith('{') or s.startswith('['):
        # 2 - Attempt to format as JSON
        return dumps(loads(s), indent=4)
    except:
        #print('Failed to format: ' + s + '\n' + traceback.format_exc())
        pass
    
    # 3 - Otherwise, insert line breaks after any of these three characters: ?&,
    return re.sub(r'([?&,])', r'\1\n', s)


def selectRow(row):
    if selectRow.selectedRow == row:
        return

    selectRow.selectedRow = row
    app.detailSheet.set_sheet_data([(item[0], addLinebreaks(item[1])) for item in rowDetails[row].items()])

    # Works pretty ok as long as there are line breaks... fails if there's no line breaks.
    app.detailSheet.set_all_cell_sizes_to_text(width = 100)

selectRow.selectedRow = -1

followingTitle = 'Following Logs - Press F to Stop Following'
notFollowingTitle = 'Stopped Following Logs - Press F to Resume Following'

def toggleFollowing(event):
    app.following = not app.following
    app.title(followingTitle if app.following else notFollowingTitle)

ok_bindings = ['single_select', 'copy', 'find', 'row_select', 'column_width_resize', 'double_click_column_resize', 'arrowkeys', 'right_click_popup_menu', 'rc_select']

class demo(tk.Tk):
    def __init__(self, extraColumns):
        tk.Tk.__init__(self)
        self.title(followingTitle)
        self.columns = ['timeStamp', 'level', 'thread', 'message', 'correlationId', 'endpoint', 'apiVersion', 'lang'] + extraColumns
        self.following = True
        self.grid_columnconfigure(0, weight = 1)
        self.grid_rowconfigure(0, weight = 1)
        self.frame = tk.Frame(self)
        self.frame.grid_columnconfigure(0, weight = 1)
        self.frame.grid_columnconfigure(1, weight = 1)
        self.frame.grid_rowconfigure(0, weight = 1)
        self.sheet = Sheet(self.frame, theme='black')
        self.sheet.headers(self.columns)
        self.sheet.enable_bindings(*ok_bindings)
        self.sheet.bind('<<SheetSelect>>', clickOnRow)
        self.frame.grid(row = 0, column = 0, sticky = "nswe")
        self.sheet.grid(row = 0, column = 0, sticky = "nswe")
        self.sheet.column_width(self.columns.index('timeStamp'),     165)
        self.sheet.column_width(self.columns.index('level'),          50)
        self.sheet.column_width(self.columns.index('correlationId'), 290)
        self.sheet.column_width(self.columns.index('endpoint'),      140)
        self.sheet.column_width(self.columns.index('apiVersion'),     30)
        self.sheet.column_width(self.columns.index('message'),       300)
        self.sheet.column_width(self.columns.index('lang'),           50)
        self.detailSheet = Sheet(self.frame, show_header = False, show_row_index = False, show_top_left = False, auto_resize_columns = 50, theme='black')
        self.detailSheet.enable_bindings(*ok_bindings)
        self.detailSheet.grid(row = 0, column = 1, sticky = 'nswe')
        self.bind_all('f', toggleFollowing)
        self.bind_all('F', toggleFollowing)

        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

if sys.stdout.isatty():
    app = demo(sys.argv[1:])

rowDetails = []
aliases = {
    '@timestamp': 'timeStamp',
    'logger_name': 'logger',
    'thread_name': 'thread'
}

aliases_reverse = {}
for k, v in aliases.items():
    aliases_reverse[v] = aliases_reverse.get(v, []) + [k]

def getData(row, column):
    for name in [column] + aliases_reverse.get(column, []):
        if name in row:
            return row[name]
    return ''

def addRow(row):
    addRow.buffer.append(tuple([getData(row, column) for column in app.columns]))
    if time() - addRow.lastCalled >= 0.01:
        flushBuffer()

def flushBuffer():
    with addRow.lock:
        copied = addRow.buffer.copy()
        if copied:
            app.sheet.insert_rows(copied, create_selections = app.following, undo = False)
            del addRow.buffer[:len(copied)]
            addRow.lastCalled = time()
            
            if app.following:
                app.sheet.see(row = app.sheet.get_total_rows() - 1, keep_xscroll = True)

def flushBufferPeriodically():
    while True:
        sleep(2)
        flushBuffer()

addRow.lock = threading.Lock()
addRow.buffer = []
addRow.lastCalled = -1

threading.Thread(target = flushBufferPeriodically).start()

def readLine(line):
    if not sys.stdout.isatty():
        print(line)
        return

    try:
        parsed = loads(line)
    except:
        parsed = {'message': line}
    rowDetails.append(parsed.copy())  # Intentionally get it before any massaging of the data is done.
    for name in ['thread_name', 'thread']:
        if name in parsed:
            parsed[name] = parsed[name][-16:]
    if 'detailMessage' in parsed:
        try:
            parsed |= parsed['detailMessage']
            del parsed['detailMessage']
        except:
            pass
    addRow(parsed)

def monitorForInput():
    while True:
        try:
            line = inputs[0].readline()
            if not line:
                break
            readLine(line)
        except:
            pass
    
thread = threading.Thread(target = monitorForInput)
thread.start()

if sys.stdout.isatty():
    app.mainloop()

thread.join()
