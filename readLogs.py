#!/usr/bin/env python3

# 1 - Keep it scrolled to the bottom? Maybe have an option to stop...
#      Moving it to a background thread kind of worked... except it seems to only pick up stuff sparatically...
#      I kind of wonder if I need to actually be on the main thread instead...
# 2 - Handle docker compose logs being passed in...
# 3 - Default behavior when nothing is passed in on stdin? Or... do nothing?
#     Probably just run docker logs? Have to somehow pick the right thing... or pick all of them... hmm...
#     If you opted for this, how would you chain it with grep?
#     I think... we could say that if you have no input, gather output from all docker logs... and if not stdout.isatty(), then put the results to stdout.
# 4 - Make the window black or something.

# Requires Python 3.9 or newer... some combination of tksheet (3.8) and ET.indent (3.9) drive that requirement, I think...

import fcntl
from json import dumps, loads
from tksheet import Sheet  # pip install tksheet
import os
import re
import selectors
import sys
import threading
import traceback
import tkinter as tk
import xml.etree.ElementTree as ET

selectedRow = -1

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
    global selectedRow
    if selectedRow == row:
        return

    selectedRow = row
    app.sheet.select_row(row, run_binding_func = False)
    app.detailSheet.total_rows(0)
    app.detailSheet.insert_rows([(item[0], addLinebreaks(item[1])) for item in rowDetails[row].items()], undo = False)

    # Works pretty ok as long as there are line breaks... fails if there's no line breaks.
    app.detailSheet.set_all_cell_sizes_to_text(width = 100)

ok_bindings = ['single_select', 'copy', 'find', 'row_select', 'column_width_resize', 'double_click_column_resize', 'arrowkeys', 'right_click_popup_menu', 'rc_select']

class demo(tk.Tk):
    def __init__(self, extraColumns):
        tk.Tk.__init__(self)
        self.columns = ['timeStamp', 'level', 'thread', 'message', 'correlationId', 'endpoint', 'apiVersion', 'lang'] + extraColumns
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
    newRow = [getData(row, column) for column in app.columns]
    app.sheet.insert_row(row = newRow, undo = False)
    app.sheet.see(row = app.sheet.get_total_rows() - 1, keep_xscroll = True)

def readLine(line):
    try:
        parsed = loads(line)
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
    except:
        #print('Failed to load: ' + line)
        pass
    else:
        print('Adding... ' + line)
        addRow(parsed)

# set sys.stdin non-blocking
orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
fcntl.fcntl(sys.stdin, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)

# register event
m_selector = selectors.DefaultSelector()
m_selector.register(sys.stdin, selectors.EVENT_READ, readLine)

def monitorForInput():
    while True:
        #line = sys.stdin.readline()
        #if not line:
        #    break
        #readLine(line)
        for k, mask in m_selector.select():
            readLine(k.fileobj.read())
    
thread = threading.Thread(target = monitorForInput).start()

app.mainloop()

thread.join()
