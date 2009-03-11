"""module 'editpar.py' -- main module for generating the EPAR task editor

$Id$

Taken from pyraf/lib/epar.py, originally signed "M.D. De La Pena, 2000 Feb. 4"
"""

#System level modules
from Tkinter import  _default_root
from Tkinter import *
from tkMessageBox import askokcancel, showwarning
import os

# pytools modules
from irafglobals import userWorkingHome
import basicpar, eparoption, filedlg, listdlg

# Constants
MINVIEW     = 500
MINPARAMS   = 25
INPUTWIDTH  = 10
VALUEWIDTH  = 21
PROMPTWIDTH = 55

# Use these values for startup geometry ***for now***
# PARENT is the main editor window
PARENTX = 50
PARENTY = 50

# DCHILD[XY] are amounts each successive child shifts
DCHILDX = 50
DCHILDY = 50

# CHILD[XY] is a PSET window
CHILDX = PARENTX
CHILDY = PARENTY

# HELP[XY] is for the help as displayed in a window
HELPX   = 300
HELPY   = 25

eparHelpString = """\
The PyRAF parameter editor window is used to edit IRAF parameter sets.  It
allows multiple parameter sets to be edited concurrently (e.g., to edit IRAF
Psets).  It also allows the IRAF task help to be displayed in a separate window
that remains accessible while the parameters are being edited.


Editing Parameters
---------------

Parameter values are modified using various GUI widgets that depend on the
parameter properties.  It is possible to edit parameters using either the mouse
or the keyboard.  Most parameters have a context-dependent menu accessible via
right-clicking that enables unlearning the parameter (restoring its value to
the task default), clearing the value, and activating a file browser that
allows a filename to be selected and entered in the parameter field.  Some
items on the right-click pop-up menu may be disabled depending on the parameter
type (e.g., the file browser cannot be used for numeric parameters.)

The mouse-editing behavior should be familiar, so the notes below focus on
keyboard-editing.  When the editor starts, the first parameter is selected.  To
select another parameter, use the Tab key (Shift-Tab to go backwards) or Return
to move the focus from item to item. The Up and Down arrow keys also move
between fields.  The toolbar buttons can also be selected with Tab.  Use the
space bar to "push" buttons or activate menus.

Enumerated Parameters
        Parameters that have a list of choices use a drop-down menu.  The space
        bar causes the menu to appear; once it is present, the up/down arrow
        keys can be used to select different items.  Items in the list have
        accelerators (underlined, generally the first letter) that can be typed
        to jump directly to that item.  When editing is complete, hit Return or
        Tab to accept the changes, or type Escape to close the menu without
        changing the current parameter value.

Boolean Parameters
        Boolean parameters appear as Yes/No radio buttons.  Hitting the space
        bar toggles the setting, while 'y' and 'n' can be typed to select the
        desired value.

Parameter Sets
        Parameter sets (Psets) appear as a button which, when clicked, brings
        up a new editor window.  Note that two (or more) parameter lists can be
        edited concurrently.  The Package and Task identification are shown
        in the window and in the title bar.

Text Entry Fields
        Strings, integers, floats, etc. appear as text-entry fields.  Values
        are verified to to be legal before being stored in the parameter. If an
        an attempt is made to set a parameter to an illegal value, the program
        beeps and a warning message appears in the status bar at the bottom of
        the window.

        To see the value of a string that is longer than the entry widget,
        either use the left mouse button to do a slow "scroll" through the
        entry or use the middle mouse button to "pull" the value in the entry
        back and forth quickly.  In either case, just click in the entry widget
        with the mouse and then drag to the left or right.  If there is a
        selection highlighted, the middle mouse button may paste it in when
        clicked.  It may be necessary to click once with the left mouse
        button to undo the selection before using the middle button.

        You can also use the left and right arrow keys to scroll through the
        selection.  Control-A jumps to the beginning of the entry, and
        Control-E jumps to the end of the entry.


The Menu Bar
-----------

File menu:

    Open...
             Load parameters from a user-specified file.  Values are not
             stored unless Execute or Save is then selected.
    Execute
             Save all the parameters, close the editor windows, and start the
             IRAF task.  This is disabled in the secondary windows used to edit
             Psets.
    Save
             Save the parameters and close the editor window.  The task is not
             executed.
    Save As...
             Save the parameters to a user-specified file.  The task is not
             executed.
    Unlearn/Defaults
             Restore all parameters to the system default values for this
             task.  Note that individual parameters can be unlearned using the
             menu shown by right-clicking on the parameter entry.
    Cancel
             Cancel editing session and exit the parameter editor.  Changes
             that were made to the parameters are not saved; the parameters
             retain the values they had when the editor was started.

Options menu:
    Display Task Help in a Window
             Help on the IRAF task is available through the Help menu.  If this
             option is selected, the help text is displayed in a pop-up window.
             This is the default behavior.
    Display Task Help in a Browser
             If this option is selected, instead of a pop-up window help is
             displayed in the user's web browser.  This requires access to
             the internet and is a somewhat experimental feature.  The HTML
             version of help does have some nice features such as links to
             other IRAF tasks.

Help menu:
    Task Help
             Display help on the IRAF task whose parameters are being edited.
             By default the help pops up in a new window, but the help can also
             be displayed in a web browser by modifying the Options.
    Editor Help
             Display this help.


Toolbar Buttons
------------

The Toolbar contains a set of buttons that provide shortcuts for the most
common menu bar actions.  Their names are the same as the menu items given
above: Execute, Save, Defaults, Cancel, and Task Help.  The Execute button is
disabled in the secondary windows used to edit Psets.

Note that the toolbar buttons are accessible from the keyboard using the Tab
and Shift-Tab keys.  They are located in sequence before the first parameter.
If the first parameter is selected, Shift-Tab backs up to the "Task Help"
button, and if the last parameter is selected then Tab wraps around and selects
the "Execute" button.
"""

class UnfoundParamError(Exception): pass


class EditParDialog(object):

    def __init__(self, theTask, parent=None, isChild=0,
                 title="PyTools Parameter Editor", childList=None,
                 resourceDir=''):

        # Call our (or a subclass's) _setTaskParsObj() method
        self._setTaskParsObj(theTask)

        # Now go back and ensure we have the full taskname
        self._canceled = False
        self._guiName = title
        self.taskName = self._taskParsObj.getName()
        self.pkgName = self._taskParsObj.getPkgname()
        self.paramList = self._taskParsObj.getParList(docopy=1)

        # Ignore the last parameter which is $nargs
        self.numParams = len(self.paramList) - 1

        # Get default parameter values for unlearn
        self._setupDefaultParamList()

        # See if there are any other applicable parameters files to open
        self._areAnyToLoad = self._showOpenButton()

        # Set all default master GUI settings, then
        # Allow subclasses to override any master GUI settings
        self._useSimpleAutoClose  = False # certain buttons close GUI also
        self._saveAndCloseOnExec  = False
        self._showExtraHelpButton = False
        self._unpackagedTaskTitle = "Task"
        self._defaultsButtonTitle = "Defaults"
        #
        self._overrideMasterSettings() # give the subclass a chance to disagree

        # Create the root window as required, but hide it
        self.parent = parent
        if self.parent == None:
            global _default_root
            if _default_root is None:
                import Tkinter
                if not Tkinter._default_root:
                    _default_root = Tkinter.Tk()
                    _default_root.withdraw()
                else:
                    _default_root = Tkinter._default_root

        # Track whether this is a parent or child window
        self.isChild = isChild

        # Set up a color for the background to differeniate parent and child
        if self.isChild:
        #    self.bkgColor = "LightSteelBlue"
            self.iconLabel = "EPAR Child"
        else:
        #    self.bkgColor = "SlateGray3"
            self.iconLabel = "EPAR Parent"
        self.bkgColor = None

        # help windows do not exist yet
        self.irafHelpWin = None
        self.eparHelpWin = None

        # no last focus widget
        self.lastFocusWidget = None

        # Generate the top epar window
        self.top = top = Toplevel(self.parent, bg=self.bkgColor, visual="best")
        if len(self.pkgName):
            self.updateTitle(self.pkgName+"."+self.taskName)
        else:
            self.updateTitle(self.taskName)
        self.top.iconname(self.iconLabel)

        # Read in the epar options database file
        optfile = "epar.optionDB"
        try:
            # User's current directory
            self.top.option_readfile(os.path.join(os.curdir,optfile))
        except TclError:
            try:
                # User's startup directory
                self.top.option_readfile(os.path.join(userWorkingHome,optfile))
            except TclError:
                try:
                    # App default
                    self.top.option_readfile(os.path.join(resourceDir,optfile))
                except TclError:
                    print "Could not read: "+optfile

        # Create an empty list to hold child dialogs
        # *** Not a good way, REDESIGN with Mediator!
        # Also, build the parent menu bar
        if (self.parent == None):
            self.top.childList = []
        elif childList is not None:
            # all children share a list
            self.top.childList = childList

        # Build the EPAR menu bar
        self.makeMenuBar(self.top)

        # Create a spacer
        Frame(self.top, bg=self.bkgColor, height=10).pack(side=TOP, fill=X)

        # Print the package and task names
        self.printNames(self.top, self.taskName, self.pkgName)

        # Insert a spacer between the static text and the buttons
        Frame(self.top, bg=self.bkgColor, height=15).pack(side=TOP, fill=X)

        # Set control buttons at the top of the frame
        self.buttonBox(self.top)

        # Insert a spacer between the static text and the buttons
        Frame(self.top, bg=self.bkgColor, height=15).pack(side=TOP, fill=X)

        # Set up an information Frame at the bottom of the EPAR window
        # RESIZING is currently disabled.
        # Do this here so when resizing to a smaller sizes, the parameter
        # panel is reduced - not the information frame.
        self.top.status = Label(self.top, text="", relief=SUNKEN,
                           borderwidth=1, anchor=W)
        self.top.status.pack(side=BOTTOM, fill=X, padx=0, pady=3,
                             ipady=3)

        # Set up a Frame to hold a scrollable Canvas
        self.top.f = frame = Frame(self.top, relief=RIDGE, borderwidth=1)

        # Overlay a Canvas which will hold a Frame
        self.top.f.canvas = canvas = Canvas(self.top.f, width=100, height=100,
            takefocus=FALSE)

        # Always build the scrollbar, even if number of parameters is small,
        # to allow window to be resized.

        # Attach a vertical Scrollbar to the Frame/Canvas
        self.top.f.vscroll = Scrollbar(self.top.f, orient=VERTICAL,
             width=11, relief=SUNKEN, activerelief=RAISED,
             takefocus=FALSE)
        canvas['yscrollcommand'] = self.top.f.vscroll.set
        self.top.f.vscroll['command'] = canvas.yview

        # Pack the Scrollbar
        self.top.f.vscroll.pack(side=RIGHT, fill=Y)

        # enable Page Up/Down keys
        scroll = canvas.yview_scroll
        top.bind('<Next>', lambda event, fs=scroll: fs(1, "pages"))
        top.bind('<Prior>', lambda event, fs=scroll: fs(-1, "pages"))

        # make up, down arrows and return/shift-return do same as Tab, Shift-Tab
        top.bind('<Up>', self.focusPrev)
        top.bind('<Down>', self.focusNext)
        top.bind('<Shift-Return>', self.focusPrev)
        top.bind('<Return>', self.focusNext)
        try:
            # special shift-tab binding needed for (some? all?) linux systems
            top.bind('<KeyPress-ISO_Left_Tab>', self.focusPrev)
        except TclError:
            # Ignore exception here, the binding can't be relevant
            # if ISO_Left_Tab is unknown.
            pass

        # Pack the Frame and Canvas
        canvas.pack(side=TOP, expand=TRUE, fill=BOTH)
        self.top.f.pack(side=TOP, expand=TRUE, fill=BOTH)

        # Define a Frame to contain the parameter information
        canvas.entries = Frame(canvas)

        # Generate the window to hold the Frame which sits on the Canvas
        cWindow = canvas.create_window(0, 0,
                           anchor=NW,
                           window=canvas.entries)

        # Insert a spacer between the Canvas and the information frame
        Frame(self.top, bg=self.bkgColor, height=4).pack(side=TOP, fill=X)

        # The parent has the control, unless there are children
        # Fix the geometry of where the windows first appear on the screen
        if (self.parent == None):
            #self.top.grab_set()

            # Position this dialog relative to the parent
            self.top.geometry("+%d+%d" % (PARENTX, PARENTY))
        else:
            #self.parent.grab_release()
            #self.top.grab_set()

            # Declare the global variables so they can be updated
            global CHILDX
            global CHILDY

            # Position this dialog relative to the parent
            CHILDX = CHILDX + DCHILDX
            CHILDY = CHILDY + DCHILDY
            self.top.geometry("+%d+%d" % (CHILDX, CHILDY))


        #
        # Now fill in the Canvas Window
        #

        # The makeEntries method creates the parameter entry Frame
        self.makeEntries(canvas.entries, self.top.status)

        # Force an update of the entry Frame
        canvas.entries.update()

        # Determine the size of the entry Frame
        width = canvas.entries.winfo_width()
        height = canvas.entries.winfo_height()

        # Reconfigure the Canvas size based on the Frame.
        if (self.numParams <= MINPARAMS):
            viewHeight = height
        else:
            # Set the minimum display
            viewHeight = MINVIEW

        # Scrollregion is based upon the full size of the entry Frame
        canvas.config(scrollregion=(0, 0, width, height))
        # Smooth scroll
        self.yscrollincrement = 50
        canvas.config(yscrollincrement=self.yscrollincrement)

        # Set the actual viewable region for the Canvas
        canvas.config(width=width, height=viewHeight)

        # Force an update of the Canvas
        canvas.update()

        # Associate deletion of the main window to a Abort
        self.top.protocol("WM_DELETE_WINDOW", self.abort)

        # Set focus to first parameter
        self.entryNo[0].focus_set()

        # Enable interactive resizing in height
        self.top.resizable(width=FALSE, height=TRUE)

        # Limit maximum window height
        width = self.top.winfo_width()
        height = self.top.winfo_height() + height - viewHeight
        self.top.maxsize(width=width, height=height)

        # run the mainloop
        if not self.isChild:
            self._preMainLoop()
            self.top.mainloop()
            self._postMainLoop()


    def _overrideMasterSettings(self):
        """ Hook for subclasses to override some attributes if wished. """
        return


    def _preMainLoop(self):
        """ Hook for subclasses to override if wished. """
        return


    def _postMainLoop(self):
        """ Hook for subclasses to override if wished. """
        return


    def _showOpenButton(self):
        """ Should we show the "Open..." button?  Subclasses override. """
        return False


    def _setTaskParsObj(self, theTask):
        """ This method, meant to be overridden by subclasses, generates the
        _taskParsObj object. theTask can often be either a file name or a
        TaskPars subclass object. """

        # Here we catch if this version is run by accident
        raise RuntimeError("Bug: EditParDialog is not to be used directly")


    def updateTitle(self, atitle):
        self.top.title('%s:  %s' % (self._guiName, atitle))


    def getTaskParsObj(self):
        """ Simple accessor.  Return the _taskParsObj object. """
        return self._taskParsObj

# A bug appeared in Python 2.3 that caused tk_focusNext and
# tk_focusPrev to fail. The follwoing two routines now will
# trap this error and call "fixed" versions of these tk routines
# instead in the event of such errors.

    def focusNext(self, event):
        """Set focus to next item in sequence"""
        try:
            event.widget.tk_focusNext().focus_set()
        except TypeError:
            # see tkinter equivalent code for tk_focusNext to see
            # commented original version
            name = event.widget.tk.call('tk_focusNext', event.widget._w)
            event.widget._nametowidget(str(name)).focus_set()

    def focusPrev(self, event):
        """Set focus to previous item in sequence"""
        try:
            event.widget.tk_focusPrev().focus_set()
        except TypeError:
            # see tkinter equivalent code for tk_focusPrev to see
            # commented original version
            name = event.widget.tk.call('tk_focusPrev', event.widget._w)
            event.widget._nametowidget(str(name)).focus_set()

    def doScroll(self, event):
        """Scroll the panel down to ensure widget with focus to be visible

        Tracks the last widget that doScroll was called for and ignores
        repeated calls.  That handles the case where the focus moves not
        between parameter entries but to someplace outside the hierarchy.
        In that case the scrolling is not expected.

        Returns false if the scroll is ignored, else true.
        """
        canvas = self.top.f.canvas
        widgetWithFocus = event.widget
        if widgetWithFocus is self.lastFocusWidget:
            return FALSE
        self.lastFocusWidget = widgetWithFocus
        if widgetWithFocus is None:
            return TRUE
        # determine distance of widget from top & bottom edges of canvas
        y1 = widgetWithFocus.winfo_rooty()
        y2 = y1 + widgetWithFocus.winfo_height()
        cy1 = canvas.winfo_rooty()
        cy2 = cy1 + canvas.winfo_height()
        yinc = self.yscrollincrement
        if y1<cy1:
            # this will continue to work when integer division goes away
            sdist = int((y1-cy1-yinc+1.)/yinc)
            canvas.yview_scroll(sdist, "units")
        elif cy2<y2:
            sdist = int((y2-cy2+yinc-1.)/yinc)
            canvas.yview_scroll(sdist, "units")
        return TRUE


    def _setupDefaultParamList(self):

        # Obtain the default parameter list
        dlist = self._taskParsObj.getDefaultParList()
        if len(dlist) != len(self.paramList):
            # whoops, lengths don't match
            raise ValueError("Mismatch between default, current par lists"
                " for task %s (try unlearn)" % self.taskName)
        # convert it to a dict
        dict = {}
        for par in dlist:
            dict[par.name] = par
        # Build default list sorted into same order as current list
        try:
            dsort = []
            for par in self.paramList:
                dsort.append(dict[par.name])
        except KeyError:
            raise ValueError("Mismatch between default, current par lists"
                " for task %s (try unlearn)" % self.taskName)
        self.defaultParamList = dsort


    # Method to create the parameter entries
    def makeEntries(self, master, statusBar):

        # Determine the size of the longest input string
        inputLength = INPUTWIDTH
        for i in range(self.numParams):
            inputString = self.paramList[i].name
            if (len(inputString) > inputLength):
                inputLength = len(inputString)

        # Set up the field widths
        # Allow extra spaces for buffer and in case the longest parameter
        # has the hidden parameter indicator
        self.fieldWidths = {}
        self.fieldWidths['inputWidth'] = inputLength + 4
        self.fieldWidths['valueWidth'] = VALUEWIDTH
        self.fieldWidths['promptWidth'] = PROMPTWIDTH

        # Loop over the parameters to create the entries
        self.entryNo = [None] * self.numParams
        for i in range(self.numParams):
            eparOpt = self._nonStandardEparOptionFor(self.paramList[i].type)
            cbo = self._defineEditedCallbackObjectFor(self.paramList[i].scope,
                                                      self.paramList[i].name)
            self.entryNo[i] = eparoption.eparOptionFactory(master, statusBar,
                                  self.paramList[i], self.defaultParamList[i],
                                  self.doScroll, self.fieldWidths,
                                  plugIn=eparOpt, editedCallbackObj=cbo)


    def _nonStandardEparOptionFor(self, paramTypeStr):
        """ Hook to allow subclasses to employ their own GUI option type.
            Return None or a class which derives from EparOption. """
        return None


    def _defineEditedCallbackObjectFor(self, parScope, parName):
        """ Hook to allow subclasses to set their own callback-containing
            object to be used when a given option/parameter is edited.
            See notes in EparOption. """
        return None


    def _isUnpackagedTask(self):
        """ Hook to allow subclasses to state that this is a rogue task, not
            affiliated with a specific package, affecting its display. """
        return self.pkgName == None or len(self.pkgName) < 1


    def _toggleSectionActiveState(self, sectionName, state, skipList):
        """ Make an entire section (minus skipList items) either active or 
            inactive.  sectionName is the same as the param's scope. """
        for i in range(self.numParams):
            if self.paramList[i].scope == sectionName and \
               not self.paramList[i].name in skipList:
                try:
                    if state:
                        self.entryNo[i].entry.configure(state=NORMAL)
                    else:
                        self.entryNo[i].entry.configure(state=DISABLED)
                except TclError:
                    pass # for now, some items don't set "-state"


    # Method to print the package and task names and to set up the menu
    # button for the choice of the display for the task help page
    def printNames(self, top, taskName, pkgName):

        topbox = Frame(top, bg=self.bkgColor)
        textbox = Frame(topbox, bg=self.bkgColor)
        helpbox = Frame(topbox, bg=self.bkgColor)

        # Set up the information strings
        if self._isUnpackagedTask():
            # label for a parameter list is just filename
            packString = " "+self._unpackagedTaskTitle+" = "+taskName
            Label(textbox, text=packString, bg=self.bkgColor).pack(side=TOP,
                  anchor=W)
        else:
            # labels for task
            packString = "  Package = " + pkgName.upper()
            Label(textbox, text=packString, bg=self.bkgColor).pack(side=TOP,
                  anchor=W)

            taskString = "       Task = " + taskName.upper()
            Label(textbox, text=taskString, bg=self.bkgColor).pack(side=TOP,
                  anchor=W)
        textbox.pack(side=LEFT, anchor=W)
        topbox.pack(side=TOP, expand=FALSE, fill=X)

    # Method to set up the parent menu bar
    def makeMenuBar(self, top):

        menubar = Frame(top, bd=1, relief=GROOVE)

        # Generate the menus
        fileMenu = self.makeFileMenu(menubar)

        # When redesigned, optionsMenu should only be on the parent
        #if not self.isChild:
        #    optionsMenu = self.makeOptionsMenu(menubar)
        optionsMenu = self.makeOptionsMenu(menubar)

        helpMenu = self.makeHelpMenu(menubar)

        menubar.pack(fill=X)


    # Method to generate a "File" menu
    def makeFileMenu(self, menubar):

        fileButton = Menubutton(menubar, text='File')
        fileButton.pack(side=LEFT, padx=2)

        fileButton.menu = Menu(fileButton, tearoff=0)

        if self._areAnyToLoad:
            fileButton.menu.add_command(label="Open...", command=self.pfopen)
            fileButton.menu.add_separator()

        fileButton.menu.add_command(label="Execute", command=self.execute)
        if self.isChild:
            fileButton.menu.entryconfigure(0, state=DISABLED)

        fileButton.menu.add_command(label="Save & Quit",command=self.save_quit)
        if not self.isChild:
            fileButton.menu.add_command(label="Save As...", command=self.saveAs)
        fileButton.menu.add_command(label=self._defaultsButtonTitle,
                                    command=self.unlearn)
        fileButton.menu.add_separator()
        fileButton.menu.add_command(label="Cancel", command=self.abort)

        # Associate the menu with the menu button
        fileButton["menu"] = fileButton.menu

        return fileButton

    # Method to generate the "Options" menu for the parent EPAR only
    def makeOptionsMenu(self, menubar):

        # Set up the menu for the HELP viewing choice
        self.helpChoice = StringVar()
        self.helpChoice.set("WINDOW")

        optionButton = Menubutton(menubar, text="Options")
        optionButton.pack(side=LEFT, padx=2)

        optionButton.menu = Menu(optionButton, tearoff=0)

        optionButton.menu.add_radiobutton(label="Display Task Help in a Window",
                                          value="WINDOW",
                                          variable=self.helpChoice)
        optionButton.menu.add_radiobutton(label="Display Task Help in a Browser",
                                          value="BROWSER",
                                          variable=self.helpChoice)

        # Associate the menu with the menu button
        optionButton["menu"] = optionButton.menu

        return optionButton

    def makeHelpMenu(self, menubar):

        button = Menubutton(menubar, text='Help')
        button.pack(side=RIGHT, padx=2)
        button.menu = Menu(button, tearoff=0)
        button.menu.add_command(label="Task Help", command=self.setHelpViewer)
        button.menu.add_command(label="Editor Help", command=self.eparHelp)
        button["menu"] = button.menu
        return button

    # Method to set up the action buttons
    # Create the buttons in an order for good navigation
    def buttonBox(self, top):

        box = Frame(top, bg=self.bkgColor, bd=1, relief=SUNKEN)

        # When the Button is exited, the information clears, and the
        # Button goes back to the nonactive color.
        top.bind("<Leave>", self.clearInfo)

        # Allow them to load/open a file if the right kind was found
        if self._areAnyToLoad:
            buttonOpen = Button(box, text="Open...",
                                relief=RAISED, command=self.pfopen)
            buttonOpen.pack(side=LEFT, padx=5, pady=7)
            buttonOpen.bind("<Enter>", self.printOpenInfo)
            # separate this button from the others - it's unusual
            strut = Label(box, text="")
            strut.pack(side=LEFT, padx=20)

        # Execute the task
        buttonExecute = Button(box, text="Execute",
                               relief=RAISED, command=self.execute)
        buttonExecute.pack(side=LEFT, padx=5, pady=7)
        buttonExecute.bind("<Enter>", self.printExecuteInfo)

        # EXECUTE button is disabled for child windows
        if self.isChild:
            buttonExecute.configure(state=DISABLED)

        # Save the parameter settings and exit from epar
        buttonQuit = Button(box, text="Save & Quit",
                            relief=RAISED, command=self.save_quit)
        buttonQuit.pack(side=LEFT, padx=5, pady=7)
        buttonQuit.bind("<Enter>", self.printQuitInfo)

        # Save all the current parameter settings to a separate file
        if not self.isChild:
            buttonSaveAs = Button(box, text="Save As...",
                                  relief=RAISED, command=self.saveAs)
            buttonSaveAs.pack(side=LEFT, padx=5, pady=7)
            buttonSaveAs.bind("<Enter>", self.printSaveAsInfo)

        # Unlearn all the parameter settings (set back to the defaults)
        buttonUnlearn = Button(box, text=self._defaultsButtonTitle,
                               relief=RAISED, command=self.unlearn)
        buttonUnlearn.pack(side=LEFT, padx=5, pady=7)
        buttonUnlearn.bind("<Enter>", self.printUnlearnInfo)

        # Abort this edit session.  Currently, if an UNLEARN has already
        # been done, the UNLEARN is kept.
        buttonAbort = Button(box, text="Cancel",
                              relief=RAISED, command=self.abort)
        buttonAbort.pack(side=LEFT, padx=5, pady=7)
        buttonAbort.bind("<Enter>", self.printAbortInfo)

        # Generate the a Help button
        buttonHelp = Button(box, text="Task Help",
                            relief=RAISED, command=self.setHelpViewer)
        buttonHelp.pack(side=RIGHT, padx=5, pady=7)
        buttonHelp.bind("<Enter>", self.printHelpInfo)

        box.pack(fill=X, expand=FALSE)


    # Determine which method of displaying the help pages was
    # chosen by the user.  WINDOW displays in a task generated scrollable
    # window.  BROWSER invokes the STSDAS HTML help pages and displays
    # in a browser.
    def setHelpViewer(self, event=None):

        value = self.helpChoice.get()
        if value == "WINDOW":
            self.help()
        else:
            self.htmlHelp()


    #
    # Define flyover help text associated with the action buttons
    #

    def clearInfo(self, event):
        self.top.status.config(text="")

    def printHelpViewInfo(self, event):
        self.top.status.config(text =
             " Choice of display for the help page: a window or a browser")

    def printHelpInfo(self, event):
        self.top.status.config(text =
             " Display the help page")

    def printUnlearnInfo(self, event):
        self.top.status.config(text =
             " Set all parameter values to system default settings")

    def printQuitInfo(self, event):
        self.top.status.config(text =
             " Save the current entries and exit this edit session")

    def printSaveAsInfo(self, event):
        self.top.status.config(text =
             " Save the current entries to a user-specified file")

    def printOpenInfo(self, event):
        self.top.status.config(text =
             " Load parameter values from a user-specified file")

    def printAbortInfo(self, event):
        self.top.status.config(text=" Abort this edit session")

    def printExecuteInfo(self, event):
        self.top.status.config(text =
             " Execute the task and exit this edit session")


    # Process invalid input values and invoke a query dialog
    def processBadEntries(self, badEntriesList, taskname):

        badEntriesString = "Task " + taskname.upper() + " --\n" \
            "Invalid values have been entered.\n\n" \
            "Parameter   Bad Value   Reset Value\n"

        for i in range (len(badEntriesList)):
            badEntriesString = badEntriesString + \
                "%15s %10s %10s\n" % (badEntriesList[i][0], \
                badEntriesList[i][1], badEntriesList[i][2])

        badEntriesString = badEntriesString + '\n"OK" to continue using'+ \
            ' the reset\nvalues or "Cancel" to re-enter\nvalues?\n'

        # Invoke the modal message dialog
        return (askokcancel("Notice", badEntriesString))


    # SAVE/QUIT: save the parameter settings and exit epar
    def save_quit(self, event=None):

        # first save the child parameters, aborting save if
        # invalid entries were encountered
        if self.checkSetSaveChildren():
            return

        # Save all the entries and verify them, keeping track of the
        # invalid entries which have been reset to their original input values
        self.badEntriesList = self.checkSetSaveEntries()

        # If there were invalid entries, prepare the message dialog
        if (self.badEntriesList):
            ansOKCANCEL = self.processBadEntries(self.badEntriesList,
                          self.taskName)
            if not ansOKCANCEL:
                return

        # If there were no invalid entries or the user says OK

        # Remove the main epar window
        self.top.focus_set()
        self.top.withdraw()

        # Do not destroy the window, just hide it for now.
        # This is so EXECUTE will not get an error - properly use Mediator.
        #self.top.destroy()

        # If not a child window, quit the entire session
        if not self.isChild:
            self.top.destroy()
            self.top.quit()

        # Declare the global variables so they can be updated
        global CHILDX
        global CHILDY

        # Reset to the start location
        CHILDX = PARENTX
        CHILDY = PARENTY


    # OPEN: load parameter settings from a user-specified file
    def pfopen(self, event=None):
        """ Load the parameter settings from a user-specified file.  Any
        changes here should be coordinated with the corresponding tpar pfopen
        function. """
        raise RuntimeError("Bug: EditParDialog is not to be used directly")


    def _getSaveAsFilter(self):
        """ Return a string to be used as the filter arg to the save file
            dialog during Save-As. Override for more specific behavior. """
        return "*.*"


    def _saveAsPreSave_Hook(self, fnameToBeUsed):
        """ Allow a subclass any specific checks right before the save. """
        return None


    def _saveAsPostSave_Hook(self, fnameToBeUsed):
        """ Allow a subclass any specific checks right after the save. """
        return None


    # SAVE AS: save the parameter settings to a user-specified file
    def saveAs(self, event=None):
        """ Save the parameter settings to a user-specified file.  Any
        changes here must be coordinated with the corresponding tpar save_as
        function. """

        # The user wishes to save to a different name
        # (could use Tkinter's FileDialog, but this one is prettier)
        fd = filedlg.SaveFileDialog(self.top, "Save Parameter File As",
                                    self._getSaveAsFilter())
        if fd.Show() != 1:
            fd.DialogCleanup()
            return
        fname = fd.GetFileName()
        fd.DialogCleanup()

        # First check the child parameters, aborting save if
        # invalid entries were encountered
        if self.checkSetSaveChildren():
            return

        # Run any subclass-specific steps right before the save
        self._saveAsPreSave_Hook(fname)

        # Verify all the entries (without save), keeping track of the invalid
        # entries which have been reset to their original input values
        self.badEntriesList = self.checkSetSaveEntries(doSave=False)

        # If there were invalid entries, prepare the message dialog
        if (self.badEntriesList):
            ansOKCANCEL = self.processBadEntries(self.badEntriesList,
                          self.taskName)
            if not ansOKCANCEL:
                return

        # If there were no invalid entries or the user says OK, finally
        # save to their stated file.  Since we have already processed the
        # bad entries, there should be none returned.
        mstr = "TASKMETA: task="+self.taskName+" package="+self.pkgName
        if self.checkSetSaveEntries(doSave=True, filename=fname, comment=mstr):
            raise Exception("Unexpected bad entries for: "+self.taskName)

        # Run any subclass-specific steps right after the save
        self._saveAsPostSave_Hook(fname)


    # EXECUTE: save the parameter settings and run the task
    def execute(self, event=None):

        # first save the child parameters, aborting save if
        # invalid entries were encountered
        if self.checkSetSaveChildren():
            return

        # Now save the parameter values of the parent
        self.badEntriesList = self.checkSetSaveEntries()

        # If there were invalid entries in the parent epar dialog, prepare
        # the message dialog
        ansOKCANCEL = FALSE
        if (self.badEntriesList):
            ansOKCANCEL = self.processBadEntries(self.badEntriesList,
                          self.taskName)
            if not ansOKCANCEL:
                return

        # If there were no invalid entries or the user says OK

        # Remove the main epar window
        self.top.focus_set()
        self.top.withdraw()
        self.top.destroy()

        print "\nTask %s is running...\n" % self.taskName

        # Run the task
        try:
            self.runTask()
        finally:
            self.top.quit()

        # Declare the global variables so they can be updated
        global CHILDX
        global CHILDY

        # Reset to the start location
        CHILDX = PARENTX
        CHILDY = PARENTY


    # ABORT: abort this epar session
    def abort(self, event=None):

        # Declare the global variables so they can be updated
        global CHILDX
        global CHILDY

        # Reset to the start location
        CHILDX = PARENTX
        CHILDY = PARENTY

        # Give focus back to parent window and abort
        self.top.focus_set()
        self.top.withdraw()

        # Note that they canceled
        self._canceled = True

        # Do not destroy the window, just hide it for now.
        # This is so EXECUTE will not get an error - properly use Mediator.
        #self.top.destroy()
        if not self.isChild:
            self.top.destroy()
            self.top.quit()


    # UNLEARN: unlearn all the parameters by setting their values
    # back to the system default
    def unlearn(self, event=None):

        # Reset the values of the parameters
        self.unlearnAllEntries(self.top.f.canvas.entries)


    # HTMLHELP: invoke the HTML help
    def htmlHelp(self, event=None):
        print "EditParDialog.htmlHelp --> UNFINISHED ..."


    # HELP: invoke help and put the page in a window
    def help(self, event=None):

        try:
            if self.irafHelpWin.state() != NORMAL:
                self.irafHelpWin.deiconify()
            self.irafHelpWin.tkraise()
            return
        except (AttributeError, TclError):
            pass
        # Acquire the task help as a string
        # Need to include the package name for the task to
        # avoid name conflicts with tasks from other packages. WJH
        helpString = self.getHelpString(self.pkgName+'.'+self.taskName)
        self.irafHelpWin = self.helpBrowser(helpString)


    # EPAR HELP: invoke help and put the epar help page in a window
    def eparHelp(self, event=None):

        try:
            if self.eparHelpWin.state() != NORMAL:
                self.eparHelpWin.deiconify()
            self.eparHelpWin.tkraise()
            return
        except (AttributeError, TclError):
            pass
        self.eparHelpWin = self.helpBrowser(eparHelpString,
                                            title='Parameter Editor Help')


    def canceled(self):
        """ Did the user click Cancel? (or close us via the window manager) """
        return self._canceled


    # Get the task help in a string
    def getHelpString(self, taskname):
        """ Provide a task-specific help string. """
        return self._taskParsObj.getHelpAsString()


    # Set up the help dialog (browser)
    def helpBrowser(self, helpString, title="Parameter Editor Help Browser"):

        # Generate a new Toplevel window for the browser
        # hb = Toplevel(self.top, bg="SlateGray3")
        hb = Toplevel(self.top, bg=None)
        hb.title(title)
        hb.iconLabel = title

        # Set up the Menu Bar
        hb.menubar = Frame(hb, relief=RIDGE, borderwidth=0)
        hb.menubar.button = Button(hb.menubar, text="Close",
                                     relief=RAISED,
                                     command=hb.destroy)
        hb.menubar.button.pack()
        hb.menubar.pack(side=BOTTOM, padx=5, pady=5)

        # Define the Frame for the scrolling Listbox
        hb.frame = Frame(hb, relief=RIDGE, borderwidth=1)

        # Attach a vertical Scrollbar to the Frame
        hb.frame.vscroll = Scrollbar(hb.frame, orient=VERTICAL,
                 width=11, relief=SUNKEN, activerelief=RAISED,
                 takefocus=FALSE)

        # Define the Listbox and setup the Scrollbar
        hb.frame.list = Listbox(hb.frame,
                                relief=FLAT,
                                height=25,
                                width=80,
                                takefocus=FALSE,
                                selectmode=SINGLE,
                                selectborderwidth=0)
        hb.frame.list['yscrollcommand'] = hb.frame.vscroll.set

        hb.frame.vscroll['command'] = hb.frame.list.yview
        hb.frame.vscroll.pack(side=RIGHT, fill=Y)
        hb.frame.list.pack(side=TOP, expand=TRUE, fill=BOTH)
        hb.frame.pack(side=TOP, fill=BOTH, expand=TRUE)

        # Insert each line of the helpString onto the Frame
        listing = helpString.split('\n')
        for line in listing:

            # Filter the text *** DO THIS A BETTER WAY ***
            line = line.replace("\x0e", "")
            line = line.replace("\x0f", "")
            line = line.replace("\f", "")

            # Insert the text into the Listbox
            hb.frame.list.insert(END, line)

        # When the Listbox appears, the listing will be at the beginning
        y = hb.frame.vscroll.get()[0]
        hb.frame.list.yview(int(y))

        # enable Page Up/Down keys
        scroll = hb.frame.list.yview_scroll
        hb.bind('<Next>', lambda event, fs=scroll: fs(1, "pages"))
        hb.bind('<Prior>', lambda event, fs=scroll: fs(-1, "pages"))

        # Position this dialog relative to the parent
        hb.geometry("+%d+%d" % (self.top.winfo_rootx() + HELPX,
                                     self.top.winfo_rooty() + HELPY))
        return hb

    def validate(self):

        return 1


    def setAllEntriesFromParList(self, aParList):
        """ Set all the parameter entry values in the GUI to the values
            in the given par list.  Note corresponding TparDisplay method. """

        if len(aParList) != len(self.paramList):
            showwarning(message="Attempting to set parameter values from a "+ \
                        "list of different length ("+str(len(aParList))+ \
                        ") than the number shown here ("+ \
                        str(len(self.paramList))+").  Be aware.",
                        title="Parameter List Length Mismatch")

        # LOOP THRU GUI PAR LIST
        for i in range(self.numParams):
            par = self.paramList[i]
            if par.type == "pset":
                continue # skip PSET's for now
            gui_entry = self.entryNo[i]

            # Set the value in self.paramList before setting it in the GUI
            # This may be in the form of a list, or an IrafParList (getValue)
            if isinstance(aParList, list):
                # Since "aParList" can have them in different order and number
                # than we do, we'll have to first find the matching param.
                found = False
                for newpar in aParList:
                    if newpar.name==par.name and newpar.scope==par.scope:
                        par.set(newpar.value) # same as .get(native=1,prompt=0)
                        found = True
                        break

                # Now see if newpar was found in our list
                if not found:
                    pnm = par.name
                    if len(par.scope): pnm = par.scope+'.'+par.name
                    raise UnfoundParamError('Error - Unfound Parameter! \n\n'+\
                      'Expected parameter "'+pnm+'" for task "'+ \
                      self._taskParsObj.getName()+'". \nThere may be others...')

            else: # assume has getValue()
                par.set(aParList.getValue(par.name, native=1, prompt=0))

            # gui holds a str, but par.value is native; conversion occurs
            gui_entry.forceValue(par.value)


    def unlearnAllEntries(self, master):
        """ Method to "unlearn" all the parameter entry values in the GUI
            and set the parameter back to the default value """
        for entry in self.entryNo:
            entry.unlearnValue()


    # Read, save, and validate the entries
    def checkSetSaveEntries(self, doSave=True, filename=None, comment=None):

        self.badEntries = []
        asNative = self._taskParsObj.knowAsNative()

        # Loop over the parameters to obtain the modified information
        for i in range(self.numParams):

            par = self.paramList[i] # IrafPar or subclass
            entry = self.entryNo[i] # EparOption or subclass
            # Cannot change an entry if it is a PSET, just skip
            if par.type == "pset":
                continue

            # get current state of par in the gui
            value = entry.choice.get()

            # Set new values for changed parameters - a bit tricky,
            # since changes that weren't followed by a return or
            # tab have not yet been checked.  If we eventually
            # use a widget that can check all changes, we will
            # only need to check the isChanged flag.
            if par.isChanged() or value != entry.previousValue:

                # CHECK: Verify the value is valid. If it is invalid,
                # the value will be converted to its original valid value.
                # Maintain a list of the reset values for user notification.
                # Always call entryCheck, no matter what type of _taskParsObj,
                # since entryCheck can do some basic type checking.
                failed = False
                if entry.entryCheck():
                    self.badEntries.append([entry.name, value,
                                           entry.choice.get()])
                    failed = True
                # See if we need to do a more serious validity check
                elif self._taskParsObj.canPerformValidation():
                    # if we are planning to save in native type, test that way
                    if asNative:
                        try:
                            value = entry.convertToNative(value)
                        except:
                            prev = entry.previousValue
                            self.badEntries.append([entry.name, value, prev])
                            entry.choice.set(prev)
                            failed = True
                    # now try the val in it's validator
                    if not failed:
                        valOK, prev = self._taskParsObj.tryValue(entry.name,
                                                        value, scope=par.scope)
                        if not valOK:
                            self.badEntries.append([entry.name,str(value),prev])
                            entry.choice.set(prev)
                            failed = True

                # get value again in case it changed - this version IS valid
                value = entry.choice.get()
                if asNative: value = entry.convertToNative(value)

                # SET: Update the task parameter (also does the conversion
                # from string)
                self._taskParsObj.setParam(par.name, value, scope=par.scope,
                                           check=0)

        # SAVE: Save results to the given file
        if doSave and not self._skipParSave_Hook():
            rv=self._taskParsObj.saveParList(filename=filename,comment=comment)
            print rv

        return self.badEntries


    def _skipParSave_Hook(self):
        """ A hook for subclasses.  Return true if the saveParList call should
            be skipped during a "Save" operation. """
        return False # default, do nothing different - save during a save


    def checkSetSaveChildren(self, doSave=True):
        """Check, then set, then save the parameter settings for
        all child (pset) windows.

        Prompts if any problems are found.  Returns None
        on success, list of bad entries on failure.
        """
        if self.isChild:
            return

        # Need to get all the entries and verify them.
        # Save the children in backwards order to coincide with the
        # display of the dialogs (LIFO)
        for n in range (len(self.top.childList)-1, -1, -1):
            self.badEntriesList = self.top.childList[n]. \
                                  checkSetSaveEntries(doSave=doSave)
            if (self.badEntriesList):
                ansOKCANCEL = self.processBadEntries(self.badEntriesList,
                              self.top.childList[n].taskName)
                if not ansOKCANCEL:
                    return self.badEntriesList
            # If there were no invalid entries or the user says OK,
            # close down the child and increment to the next child
            self.top.childList[n].top.focus_set()
            self.top.childList[n].top.withdraw()
            del self.top.childList[n]
        # all windows saved successfully
        return

    # Run the task
    def runTask(self):

        # Use the run method of the IrafTask class
        # Set mode='h' so it does not prompt for parameters (like IRAF epar)
        # Also turn on parameter saving
        self._taskParsObj.run(mode='h', _save=1)
