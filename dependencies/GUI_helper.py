"""
GUI

Short description:
----------
Convenient classes to make using tkinter object manipulation easier and have a more
convenient interface.

Contains:
----------
- InboxGrid: A combined label and entry with set, get and destroy methods, placed with grid
- InboxPlace: A combined label and entry with set, get and destroy methods, placed with place
- InboxPack: A combined label and entry with set, get and destroy methods, placed with pack
- DirectoryInbox: A combined label, entry and button for inputing a directory path. 
- SaveFileInbox: A combined label, entry and button for inputing a save file path (does not need to exist). 
- FileInbox: A combined label, entry and button for inputing a file path (must exist).
- PlotCanvas: A combined tkinter FigureCanvasTkAgg, NavigationToolbar2Tk and the figure and axis matplotlib objects
- function popupYesNo: Opens a window and asks a question, returns True if yes, False is no

@author: Christoffer Askvik Faugstad (christoffer.askvik.faugstad@hotmail.com)
"""
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from typing import Iterable


class InboxGrid:
    """Inbox with a combined label and entry, here placed with the grid method"""

    def __init__(
        self,
        window: tk.Tk,
        text: str,
        row: int,
        column: int,
        place_under: bool = True,
        width: int = 30,
        borderwidth: int = 5,
    ):
        """
        Parameters:
        ----------
        - window: tkinter window to have the inbox in
        - text: the name of the inbox (label text)
        - row: what row to place inbox
        - column: what column to place inbox
        - place_under: If True the entry is placed underneath the label,
            if False the entry is placed to the left of the label.
        - width: Width of the entry in characters
        - borderwidth: Borderwith of entry in pixels
        """
        self.width = width
        self.borderwidth = borderwidth
        self.label = tk.Label(window, text=text)
        self.entry = tk.Entry(window, width=self.width, borderwidth=self.borderwidth)
        self.label.grid(row=row, column=column)
        if place_under == True:
            self.entry.grid(row=row + 1, column=column)
        else:
            self.entry.grid(row=row, column=column + 1)

    def get(self):
        return self.entry.get()

    def set(self, in_str: str):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, in_str)

    def destroy(self):
        self.label.destroy()
        self.entry.destroy()


class InboxPlace:
    """Inbox with a combined label and entry, here placed with the place method"""

    def __init__(
        self,
        window: tk.Tk,
        text: str,
        x: int,
        y: int,
        width: int = 30,
        borderwidth: int = 5,
    ):
        """
        Parameters:
        ----------
        - window: tkinter window to have the inbox in
        - text: the name of the inbox (label text)
        - x: what x pixel location to place inbox
        - y: what y pixel location to place inbox
        - width: Width of the entry in characters
        - borderwidth: Borderwith of entry in pixels

        Note:
        ----------
        - The entry will always be placed underneight the label.
        """
        self.width = width
        self.borderwidth = borderwidth
        self.label = tk.Label(window, text=text)
        self.entry = tk.Entry(window, width=self.width, borderwidth=self.borderwidth)
        self.label.place(x=x, y=y)
        self.entry.place(x=x, y=y + 16 + 10)

    def get(self):
        return self.entry.get()

    def set(self, in_str: str):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, in_str)

    def destroy(self):
        self.label.destroy()
        self.entry.destroy()


class InboxPack:
    """Inbox with a combined label and entry, here placed with the pack method"""

    def __init__(self, window: tk.Tk, text: str, width: int = 30, borderwidth: int = 5):
        """
        Parameters:
        ----------
        - window: tkinter window to have the inbox in
        - text: the name of the inbox (label text)
        - width: Width of the entry in characters
        - borderwidth: Borderwith of entry in pixels

        Note:
        ----------
        - The entry will be paked after the label.
        """
        self.width = width
        self.borderwidth = borderwidth
        self.label = tk.Label(window, text=text)
        self.entry = tk.Entry(window, width=self.width, borderwidth=self.borderwidth)
        self.label.pack()
        self.entry.pack()

    def get(self):
        return self.entry.get()

    def set(self, in_str: str):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, in_str)

    def destroy(self):
        self.label.destroy()
        self.entry.destroy()


class DirectoryInbox(InboxGrid):
    """
    Creates an inbox (label and entry) together with a button to browse
    in file explorer for a directory(folder).
    """

    def __init__(
        self,
        window: tk.Tk,
        text: str,
        row: int,
        column: int,
        button_text="Browse folders",
        width: int = 30,
        borderwidth: int = 5,
    ):
        """
        Parameters:
        ----------
        - window: tkinter window to have the inbox in
        - text: the name of the inbox (label text)
        - row: what row to place inbox
        - column: what column to place inbox
        - button_text: The text that shall be displayed on the browse button
        - width: Width of the entry in characters
        - borderwidth: Borderwith of entry in pixels

        Notes:
        ----------
        The widgets will be placed as
        label
        entry   browse_button
        """
        InboxGrid.__init__(
            self,
            window,
            text,
            row,
            column,
            place_under=True,
            width=width,
            borderwidth=borderwidth,
        )
        self.browse_button = tk.Button(
            window, text=button_text, command=self.browse_files
        )
        self.browse_button.grid(row=row + 1, column=column + 1)

    def browse_files(self):
        file_path = tk.filedialog.askdirectory(
            initialdir="/",
            title=self.browse_button["text"],  # Start directory
        )
        self.entry.delete(0, tk.END)
        self.entry.insert(0, file_path)


class SaveFileInbox(InboxGrid):
    """
    Creates an inbox (label and entry) together with a button to browse
    in file explorer for a save file, i.e. the file does not need to exsist.
    """

    def __init__(
        self,
        window: tk.Tk,
        text: str,
        row: int,
        column: int,
        filetypes,
        default_extension,
        button_text="Browse files",
        width: int = 30,
        borderwidth: int = 5,
    ):
        """
        Parameters:
        ----------
        - window: tkinter window to have the inbox in
        - text: the name of the inbox (label text)
        - row: what row to place inbox
        - column: what column to place inbox
        - filestypes: the allowed filetypes. On the format of a tuple as
            ((filename,"*.file_ending"),(filename,"*.file_ending"),...)
        - default_extension: The file ending to put on the end of filename if no
            ending is choosen
        - button_text: The text that shall be displayed on the browse button
        - width: Width of the entry in characters
        - borderwidth: Borderwith of entry in pixels

        Notes:
        ----------
        The widgets will be placed as
        label
        entry   browse_button
        """
        InboxGrid.__init__(
            self,
            window,
            text,
            row,
            column,
            place_under=True,
            width=width,
            borderwidth=borderwidth,
        )
        self.filetypes = filetypes
        self.default_extension = default_extension
        self.browse_button = tk.Button(
            window, text=button_text, command=self.browse_files
        )
        self.browse_button.grid(row=row + 1, column=column + 1)

    def browse_files(self):
        file_path = tk.filedialog.asksaveasfilename(
            initialdir="/",
            title=self.browse_button["text"],
            filetypes=self.filetypes,
            defaultextension=self.default_extension,
        )
        self.entry.delete(0, tk.END)
        self.entry.insert(0, file_path)


class FileInbox(InboxGrid):
    """
    Creates an inbox (label and entry) together with a button to browse
    in file explorer for a file, i.e. the file have to exsist.
    """

    def __init__(
        self,
        window: tk.Tk,
        text: str,
        row: int,
        column: int,
        filetypes,
        button_text="Browse files",
        width: int = 30,
        borderwidth: int = 5,
    ):
        """
        Parameters:
        ----------
        - window: tkinter window to have the inbox in
        - text: the name of the inbox (label text)
        - row: what row to place inbox
        - column: what column to place inbox
        - filestypes: the allowed filetypes. On the format of a tuple as
            ((filename,"*.file_ending"),(filename,"*.file_ending"),...)
        - button_text: The text that shall be displayed on the browse button
        - width: Width of the entry in characters
        - borderwidth: Borderwith of entry in pixels

        Notes:
        ----------
        The widgets will be placed as
        label
        entry   browse_button
        """
        InboxGrid.__init__(
            self,
            window,
            text,
            row,
            column,
            place_under=True,
            width=width,
            borderwidth=borderwidth,
        )
        self.filetypes = filetypes
        self.browse_button = tk.Button(
            window, text=button_text, command=self.browse_files
        )
        self.browse_button.grid(row=row + 1, column=column + 1)

    def browse_files(self):
        file_path = tk.filedialog.askopenfilename(
            initialdir="/",  # Start directory
            title=self.browse_button["text"],
            filetypes=self.filetypes,
        )
        self.entry.delete(0, tk.END)
        self.entry.insert(0, file_path)


def popupYesNo(question, title, icon="question") -> bool:
    """
    Does:
    ----------

    Function that creates a popup window and asks a yes/no
    question. And returns True if yes and False if no.

    Parameters:
    ----------
    - question: A string with the question that should be asked
    - title: A string with the title of the popup window
    - icon: either 'question','error','info' or 'warning' to change what icon is displayed

    """
    MsgBox = tk.messagebox.askquestion(title, question, icon=icon)
    return MsgBox == "yes"


class PlotCanvas:
    def __init__(
        self,
        window: tk.Tk,
        figsize,
        dpi: int,
        row: int,
        column: int,
        num_vertical_subplots: int = 1,
        num_horizontal_subplots: int = 1,
        **subplots_kwargs
    ):
        """
        Creates a canvas and toolbar and places it in the window. In additon a figure is
        created and the axis(es) are created from figure.subplots(num_vertical_subplots,
        num_horizontal_subplots,**subplots_kwargs)

        Parameters:
        ----------
        - window: Tkinter window the canvas should be displayed on
        - figsize: The figure size in inches as (horizontal length, vertical length)
        - dpi: The number of dots(pixels) per inch in the figure
        - row: What row to place the canvas in
        - column: What column to place the canvas in
        - num_vertical_subplots: How many vertical subplots the should be
        - num_horizontal_subplots: How many horizontal subplots the should be
        - **subplot_kwargs: keyword arguments pased to the figure.subplots function

        """
        # Initializing
        self.figure = Figure(figsize=figsize, dpi=dpi)
        self.axis = self.figure.subplots(
            num_vertical_subplots, num_horizontal_subplots, **subplots_kwargs
        )
        self.canvas = FigureCanvasTkAgg(self.figure, master=window)
        self.toolbar = NavigationToolbar2Tk(self.canvas, window, pack_toolbar=False)
        self.twin_axis = None
        # Placing the widgets
        self.canvas.get_tk_widget().grid(row=row, column=column)
        self.toolbar.grid(row=row + 1, column=column)
        self.toolbar.update_idletasks()

        # self.toolbar.update()

    @classmethod
    def place(
        cls,
        window: tk.Tk,
        figsize,
        dpi: int,
        x: int,
        y: int,
        num_vertical_subplots: int = 1,
        num_horizontal_subplots: int = 1,
        **subplots_kwargs
    ):
        """
        Creates a canvas and toolbar and places it in the window. In additon a figure is
        created and the axis(es) are created from figure.subplots(num_vertical_subplots,
        num_horizontal_subplots,**subplots_kwargs)

        Parameters:
        ----------
        - window: Tkinter window the canvas should be displayed on
        - figsize: The figure size in inches as (horizontal length, vertical length)
        - dpi: The number of dots(pixels) per inch in the figure
        - x: what x pixel location to place the canvas
        - y: what y pixel location to place the canvas
        - num_vertical_subplots: How many vertical subplots the should be
        - num_horizontal_subplots: How many horizontal subplots the should be
        - **subplot_kwargs: keyword arguments pased to the figure.subplots function

        """
        out = cls(
            window,
            figsize,
            dpi,
            0,
            0,
            num_vertical_subplots=num_vertical_subplots,
            num_horizontal_subplots=num_horizontal_subplots,
            **subplots_kwargs
        )
        # grid_forget to remove the grid placement and place, the place the canvas again
        out.canvas.get_tk_widget().grid_forget()
        out.canvas.get_tk_widget().place(x=x, y=y)
        out.twin_axis = None
        out.toolbar.grid_forget()
        out.toolbar.place(x=x + (figsize[0] * dpi - 300) / 2, y=y + figsize[1] * dpi)
        out.toolbar.update_idletasks()
        # returning the object
        return out

    def get_canvas(self):
        return self.canvas

    def get_axis(self):
        return self.axis

    def get_figure(self):
        return self.figure

    def get_toolbar(self):
        return self.toolbar

    def clear(self) -> None:
        """Clears the axises"""
        # Checking if more than one axis
        if isinstance(self.axis, Iterable):
            for axis in self.axis:
                # Seting scale to linear if log so clear do not fail
                if axis.get_yscale() == "log":
                    axis.set_yscale("linear")
                if axis.get_xscale() == "log":
                    axis.set_xscale("linear")

                axis.clear()
        else:
            # Seting scale to linear if log so clear do not fail
            if self.axis.get_yscale == "log":
                self.axis.set_yscale("linear")
            if self.axis.get_xscale == "log":
                self.axis.set_xscale("linear")

            self.axis.clear()
        if not self.twin_axis is None:
            for twinax in self.twin_axis:
                twinax.clear()

    def update(self) -> None:
        """Updates the axis(es)"""
        self.canvas.draw_idle()

    def remove(self) -> None:
        """Remove the canvas and its axsis"""
        self.axis.clear()
        self.figure.clear()
        # Try if it is placed with place
        try:
            self.canvas.get_tk_widget().place_forget()
            self.canvas.get_tk_widget().delete()
        # If not do it with grid_forget
        except:
            self.canvas.get_tk_widget().grid_forget()
            self.canvas.get_tk_widget().delete()
        # Set attributes to None
        self.axis = None
        self.figure = None
        self.canvas = None
