#!/usr/bin/env python3

# 1 - Give directions for installing/using.
# 2 - Handle docker compose logs being passed in...
# 3 - Default behavior when nothing is passed in on stdin? Or... do nothing?
#     Probably just run docker logs? Have to somehow pick the right thing... or pick all of them... hmm...
#     If you opted for this, how would you chain it with grep?
#     I think... we could say that if you have no input, gather output from all docker logs... and if not stdout.isatty(), then put the results to stdout.
# 4 - Make the window black or something.

# Requires Python 3.9 or newer... some combination of tksheet (3.8) and ET.indent (3.9) drive that requirement, I think...

from json import dumps, loads
from tksheet import Sheet  # pip install tksheet
import re
import sys
import threading
from time import sleep, time
import traceback
import tkinter as tk
import xml.etree.ElementTree as ET

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
        self.sheet = Sheet(self.frame)
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
        self.detailSheet = Sheet(self.frame, show_header = False, show_row_index = False, show_top_left = False, auto_resize_columns = 50)
        self.detailSheet.enable_bindings(*ok_bindings)
        self.detailSheet.grid(row = 0, column = 1, sticky = 'nswe')
        self.bind_all('f', toggleFollowing)
        self.bind_all('F', toggleFollowing)

        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")

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
            line = sys.stdin.readline()
            if not line:
                break
            readLine(line)
        except:
            pass
    
thread = threading.Thread(target = monitorForInput)
thread.start()

app.mainloop()

thread.join()
