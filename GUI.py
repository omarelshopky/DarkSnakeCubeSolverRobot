"""
#############################################################################################################
# 
# GUI for DarkSnake, a very small and simple Rubik's cube solver robot.
# 
# The GUI is built over the one from Andrea Favero who edit Mr. Kociemba GUI: https://github.com/hkociemba/RubiksCube-TwophaseSolver;
# Credits to Mr. Kociemba for the GUI, in addition to the TwoPhasesSolver!
# 
# This GUI aims to get the cube status, to communicate with the Kociemba TwophaseSolver (getting the cube solving
# manoeuvres) and finally to interact with the DarkSnake robot;
# During the cube solving process by the robot, the GUI updates the cube status sketch accordingly.
# 
# The cube status can be entered manually, or it can be acquired via a webcam by manually presenting the cube faces.
# The GUI has a setting page, with the most relevant settings for the robot, and the webcam
# 
# Manoeuvres to DarkSnake robot are sent as a tipical cube solution string, after removing empty spaces,
# with "<" and ">" characters used as conwtrols to ensure the full string is received by the robot UART.
# Other commands to the robot are sent in between square brackets, to only process complete strings
#
#############################################################################################################
"""



# ################################## Imports  ##########################################################################

# custom libraries
import colors_recognition as cam        # recognize cube status via a webcam (by Andrea Favero)
import Cubotino_moves as cm          # translate a cube solution into CUBOTino robot moves (by Andrea Favero)
import twophase.solver as sv                  # Kociemba solver library (by Hergbert Kociemba)
import twophase.face                          # Kociemba solver library (by Hergbert Kociemba)
import twophase.cubie                         # Kociemba solver library (by Hergbert Kociemba)
print()

# python libraries, normally distributed with python
import tkinter as tk                 # GUI library
from tkinter import ttk              # GUI library
import datetime as dt                # date and time library used as timestamp on a few situations (i.e. data log)
import threading                     # threading library, to parallelize uart data 
import time                          # 
import json                          # Serialize and Deserialize json objects
import requests                      # HTTP requests library to communicate with nodeMCU
import os                            # os is imported to ensure the file presence, check/make

# python library, to be installed (pyserial)
import serial.tools.list_ports

########################################################################################################################





# #################### function to load settings to global variables  #############################


def get_cam_settings(cam_settings):
    """ Function to assign the cam related settings into individual variables, based on the tupple in argument."""
    
    global cam_number, cam_width, cam_height, cam_crop, facelets_in_width #, cam_settings
    
    cam_number = cam_settings[0]         # cam number 
    cam_width = cam_settings[1]          # cam width (pixels) 
    cam_height = cam_settings[2]         # cam height (pixels)
    cam_crop = cam_settings[3]           # amount of pixel to crop at the frame right side 
    facelets_in_width = cam_settings[4]  # min number of facelets side, in frame width, to filter out too smal squares


########################################################################################################################





# ################################## global variables and constants ###################################################

# Files contain Configuration
ROBOT_SETTINGS_FILE = "robot_settings.json"
CAM_SETTINGS_FILE = "cam_settings.txt"

# width of a facelet in pixels, to draw the unfolded cube sketch
width = 70                     # many other widgets and positions, are based to this variable

facelet_id = [[[0 for col in range(3)] for row in range(3)] for fc in range(6)]    # list for the facelets GUI id
colorpick_id = [0 for i in range(6)]                           # list for the colors GUI id
faceletter_id = [0 for i in range(6)]                          # list for the faces letters GUI id

t = ("U", "R", "F", "D", "L", "B")                                  # tuple with faces identifier and related order
base_cols = ["white", "red", "green", "yellow", "orange", "blue"]   # list with colors initially associated to the cube
gray_cols = ["gray50", "gray52", "gray54", "gray56", "gray58", "gray60"]  # list with gray nuances for cube scrambling
# gray_cols = ["white", "red", "green", "purple", "orange", "blue"]

cols = base_cols.copy()        # list with colors initially associated to the cube

curcol = None                  # current color, during colorpick function and sketch color assignment
last_col=5                     # integer variable to track last color used while scrolling over the sketch
last_facelet_id = 0            # integer variable to track last facelet colored uwith mouse wheel scroll
gui_read_var=""                # string variable used for the radiobuttons, on cube status detection mode
gui_webcam_num=0               # integer variable used for the webcam number at radiobutton
cam_number=0                   # integer variable used for the webcam id number in CV
cam_width=640                  # integer variable used for the webcam width (pixels)
cam_height=360                 # integer variable used for the webcam height (pixels)
cam_crop=0                     # integer variable used to crop the right frame side (pixels)
facelets_in_width =11          # integer variable for min amount of facelets in frame width, to filter small squares
mainWindow_ontop=False         # boolean to track the main window being (or not) the raised one

cube_solving_string=""         # string variable holding the cube solution manoeuvres, as per Kociemba solver
cube_solving_string_robot=""   # string variable holding the string sent to the robot
gui_buttons_state="active"     # string variable used to activate/deactivate GUI buttons according to the situations
robot_working=False            # boolean variable to track the robot working condition, initially False
serialData=False               # boolean variable to track when the serial data can be exchanged, initially False
robot_moves=""                 # string variable holding all the robot moves (robot manoeuvres)
cube_status={}                 # dictionary variable holding the cube status, for GUI update to robot permutations
left_moves={}                  # dictionary holding the remaining robot moves


timestamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')    # timestamp used on logged data and other locations

try: 
    with open(ROBOT_SETTINGS_FILE, "r") as f:  # open the servos settings json file in read mode
        global robot_settings

        robot_settings = json.load(f)                        # returns JSON object as a dictionary              
except:
    print(f"Something is wrong with {ROBOT_SETTINGS_FILE} file")



try: 
    with open(CAM_SETTINGS_FILE, "r") as f: # open the webcam settings text file in read mode
        data = f.readline()                           # data is on first line
        data = data.replace(' ','')                   # empty spaces are removed
        if '(' in data and ')' in data:               # case the data contains open and close parenthesis
            data_start = data.find('(')               # position of open parenthesys in data
            data_end = data.find(')')                 # position of close parenthesys in data
            data = data[data_start+1:data_end]        # data in between parenthesys is re-assigned, to the same variable
            data_list=data.split(',')                 # data is split by comma, becoming a list of strings 
            
            cam_settings=[]                           # empty list to store the list of numerical settings
            for setting in data_list:                 # iteration over the list of strings
                cam_settings.append(int(setting))     # elements are converted to integer and appended
            get_cam_settings(cam_settings)            # call to the function that makes global these cam settings  

except:
    print(f"Something is wrong with {CAM_SETTINGS_FILE} file")
########################################################################################################################






# ################################################ Functions ###########################################################

def show_window(window):
    """Function to bring to the front the window in argument."""
    
    global mainWindow_ontop, app_width, app_height
    
    if window==settingWindow:                           # case the request is to show the settings windows
        settingWindow.tkraise()                         # settings windows is raised on top
        root.minsize(max(app_width,1146), app_height)   # min GUI size, preventing resizing on screen, for setting_window
        root.maxsize(max(app_width,1146), app_height)   # max GUI size, preventing resizing on screen, for setting_window
        mainWindow_ontop=False                 # boolean of main windows being on top is set false
        gui_sliders_update('update_sliders')   # calls the function to update the sliders on the (global) variables
        return                                 # function in closed
    
    elif window==mainWindow:                   # case the request is to show the main windows          
        window.tkraise()                       # main windows is raised on top
        root.minsize(app_width, app_height)    # min GUI size, that prevents resizing on screen
        root.maxsize(app_width, app_height)    # max GUI size, that prevents resizing on screen
        mainWindow_ontop=True                  # boolean of main windows being on top is set true






def show_text(txt):
    """Display messages on text window."""
    
    gui_text_window.insert(tk.INSERT, txt)      # tk function for text insert
    gui_canvas.update_idletasks()               # canvas is re-freshed






def create_facelet_rects(a):
    """ Initialize the facelet grid on the canvas."""
    
    offset = ((1, 0), (2, 1), (1, 1), (1, 2), (0, 1), (3, 1))  # coordinates (in cube face units) for cube faces position
    
    for f in range(6):                                   # iteration over the six cube faces
        for row in range(3):                             # iteration over three rows, of cube facelests per face
            y = 20 + offset[f][1] * 3 * a + row * a      # top left y coordinate to draw a rectangule
            for col in range(3):                         # iteration over three columns, of cube facelests per face
                x = 20 + offset[f][0] * 3 * a + col * a  # top left x coordinate to draw a rectangule
                
                # the list of graphichal facelets (global variable) is populated, and initially filled in grey color
                facelet_id[f][row][col] = gui_canvas.create_rectangle(x, y, x + a, y + a, fill="grey65", width=2)
    
    for f in range(6):  # iteration over the 6 faces
        gui_canvas.itemconfig(facelet_id[f][1][1], fill=cols[f]) # centers face facelets are colrored as per cols list
    
    face_letters(a)   # call the function to place URFDLB letters on face center facelets
    draw_cubotino()   # calls the funtion to draw Cubotino sketch






def face_letters(a):
    """ Add the face letter on central facelets."""
    
    offset = ((1, 0), (2, 1), (1, 1), (1, 2), (0, 1), (3, 1))  # coordinates (in cube face units) for cube faces position
    for f in range(6):                                   # iteration over the six cube faces
        y = 20 + offset[f][1] * 3 * a + a                # y coordinate for text placement
        x = 20 + offset[f][0] * 3 * a + a                # x coordinate for text placement
        
        # each of the URFDLB letters are placed on the proper cuvbe face
        faceletter_id[f]=gui_canvas.create_text(x + width // 2, y + width // 2, font=("", 18), text=t[f], fill="black")






def create_colorpick(a):
    """Initialize the "paintbox" on the canvas."""
    
    global curcol, cols
    
    cp = tk.Label(gui_canvas, text="color picking")      # gui text label informing the color picking concept
    cp.config(font=("Arial", 18))                        # gui text font is set
    
    # gui text label for colo picking info is placed on the canvas
    hp_window = gui_canvas.create_window(int(8.25 * width), int(6.45 * width), anchor="nw", window=cp)
    
    for i in range(6):                                   # iteration over the six cube faces
        x = int((i % 3) * (a + 15) + 7.65 * a)           # x coordinate for a color palette widget
        y = int((i // 3) * (a + 15) + 7 * a)             # y coordinate for a color palette widget
        
        # round widget, filled with color as per cols variable, and with tick border (20) of same gui background color
        colorpick_id[i] = gui_canvas.create_oval(x, y, x + a, y + a, fill=cols[i], width=20, outline="#F0F0F0")
        
        # the first widget is modified by reducing the border width and changing the borger color to a different gray
        gui_canvas.itemconfig(colorpick_id[0], width=5, outline="Grey55" ) 
        curcol = cols[0]    # the first color of cols tupple is assigned to the (global) current color variable






def draw_cubotino():
    """ Draw a cube and a Cubotino robot.
        This has a decorative purpose, aiming to clearly suggest the initial cube orientation on Cubotino
        (when the faces aren"t detected directly by the robot).
        Graphical widgets are all hard coded, and all referring to a single starting "(s) coordinate."""
    
    s= 5,5      # starting point coordinates to the gui_canvas2 origin
  
    # Cubotino frame
    # tuple with three tuples, holding the coordinated for the three Cubotino frame panels 
    frm_faces=((s[0],s[1]+140, s[0]+80, s[1]+190, s[0]+80, s[1]+125,s[0], s[1]+80),
               (s[0]+80, s[1]+190, s[0]+190, s[1]+105, s[0]+190, s[1]+80, s[0]+80,s[1]+125),
               (s[0]+80, s[1]+125, s[0]+190, s[1]+80, s[0]+110, s[1]+47, s[0],s[1]+80))    
    for i in range(3):      # iteration over the three tuples
        pts=frm_faces[i]    # coordinates
        gui_canvas2.create_polygon(pts, outline = "black", fill = "burlywood3", width = 1) # Cubotino frame panels drawn
    
    
    # cube on Cubotino
    # tuple with three tuples, holding the coordinated for the three faces of the cube on Cubotino sketch
    cube_faces=((s[0]+30, s[1]+80, s[0]+86, s[1]+111, s[0]+86, s[1]+42, s[0]+30, s[1]+16),
                (s[0]+86, s[1]+111, s[0]+150, s[1]+88, s[0]+150,s[1]+24, s[0]+86, s[1]+42),
                (s[0]+86, s[1]+42, s[0]+150, s[1]+24, s[0]+96, s[1]+1, s[0]+30, s[1]+16))
    for i in range(3):         # iteration over the three tuples with coordinates
        pts=cube_faces[i]      # coordinates
        gui_canvas2.create_polygon(pts, outline = "black", fill = "grey65", width = 2)  # Cube faces are drawn on Cubotino
    
    # draw cube lines, in between the facelets, on the Cubotino 
    thck=2                                                           # line thickness
    fclt_lines_pts=((s[0]+46, s[1]+24, s[0]+112, s[1]+9),    # U     # couple of coordinates per line, located at U face
                    (s[0]+65, s[1]+33, s[0]+131, s[1]+16),   # U
                    (s[0]+54, s[1]+12, s[0]+108, s[1]+36),   # U
                    (s[0]+73, s[1]+6, s[0]+131, s[1]+32),    # U
                    (s[0]+86, s[1]+65, s[0]+150, s[1]+46),   # R     # couple of coordinates per line, located at R face
                    (s[0]+86, s[1]+88, s[0]+150, s[1]+67),   # R
                    (s[0]+108, s[1]+36, s[0]+108, s[1]+104), # R
                    (s[0]+131, s[1]+32, s[0]+131, s[1]+97),  # R
                    (s[0]+30, s[1]+38, s[0]+86, s[1]+65),    # F     # couple of coordinates per line, located at F face
                    (s[0]+30, s[1]+59, s[0]+86, s[1]+88),    # F
                    (s[0]+47, s[1]+23, s[0]+47, s[1]+91),    # F
                    (s[0]+65, s[1]+32, s[0]+65, s[1]+100))   # F
    
    for i in range(len(fclt_lines_pts)):   # iteration over the tuple with coordinates for facelets lines
        gui_canvas2.create_line(fclt_lines_pts[i], width=thck)   # lines are drawn
        
    draw_cubotino_center_colors() # draw the cube center facelets with related colors






def draw_cubotino_center_colors():
    """ Fills the color on center facelets at cube on the Cubotino sketch (three visible sides)."""
    
    s= 5,5                # starting point coordinates to the gui_canvas2 origin
    fclt_col=[]           # emplty list to be populated with center faces colors on the unfolded cube sketch
    for i in range(3):    # iteration stops on three, as only the first three faces are presented on the Cubotino sketch
        fclt_col.append(gui_canvas.itemcget(facelet_id[i][1][1], "fill"))  # center faces colors are retrieved, and listed
    
    # tuple with three tuples, holding the coordinated for center faces of the three visible cube faces on Cubotino sketch 
    fclt_pts=((s[0]+70, s[1]+19, s[0]+89, s[1]+28, s[0]+107, s[1]+21, s[0]+90, s[1]+14),
              (s[0]+109, s[1]+80, s[0]+130, s[1]+74, s[0]+130, s[1]+53, s[0]+109, s[1]+59),
              (s[0]+47, s[1]+67, s[0]+64, s[1]+76, s[0]+64, s[1]+55, s[0]+47, s[1]+47))
    
    for i in range(3):  # iteration over the three tuples, for the center facelets of Cubotino sketch
        # Cube center faces colored on Cubotino
        gui_canvas2.create_polygon(fclt_pts[i], outline = "black", fill = fclt_col[i], width = 1) 






def get_definition_string():
    """Generate the cube definition string, from the facelet colors."""
    
    color_to_facelet = {}           # dict to store the color of the 54 facelets
    for i in range(6):              # iteration over the six cube faces
        # populate the dict connecting the face descriptors (UFRDLB) to center face colors (keys, 'white', 'red', etc)
        color_to_facelet.update({gui_canvas.itemcget(facelet_id[i][1][1], "fill"): t[i]})
    s = ""                          # empty string variable to be populated with the cube status
    for f in range(6):              # iteration over the six cube faces
        for row in range(3):        # iteration over the three rows of facelets 
            for col in range(3):    # iteration over the three columns of facelets
                
                # cube status string is generated by adding the colors retrieved from the 54 facelets (cube sketch)
                s += color_to_facelet[gui_canvas.itemcget(facelet_id[f][row][col], "fill")]
    return s    






def solve():
    """Connect to Kociemba solver to get the solving maneuver."""
    
    global cols, sv, b_read_solve, cube_solving_string, cube_defstr
    global cube_status, robot_moves, tot_moves, previous_move
    
    b_robot["state"] = "disable"         # GUI robot button is disabled at solve() function start
    b_robot["relief"] = "sunken"         # GUI robot button is sunk at solve() function start
    
    if gui_scramble_var.get():                   # case the scramble check box is checked
        if cols != gray_cols.copy():             # case the cube sketch is not made with gray colored facelets
            cols = gray_cols.copy()              # list with gray nuances is used instead of the cube colors
            try:
                for f in range(6):               # iteration over the six cube faces
                    for row in range(3):         # iteration over the three rows of facelets 
                        for col in range(3):     # iteration over the three columns of facelets
                            color=gray_cols[base_cols.index(gui_canvas.itemcget(facelet_id[f][row][col], "fill"))]
                            gui_canvas.itemconfig(facelet_id[f][row][col], fill=color)
            except:
                print("exception at row 410")

    elif not gui_scramble_var.get():             # case the scramble check box is not checked
        if cols == gray_cols.copy():             # case the cube sketch is made with gray colored facelets
            cols = base_cols.copy()              # list with colors initially associated to the cube
            try:
                for f in range(6):                   # iteration over the six cube faces
                    for row in range(3):             # iteration over the three rows of facelets 
                        for col in range(3):         # iteration over the three columns of facelets
                            color=base_cols[gray_cols.index(gui_canvas.itemcget(facelet_id[f][row][col], "fill"))]
                            gui_canvas.itemconfig(facelet_id[f][row][col], fill=color)
            except:
                print("exception at row 422")
                
    for i in range(6):                   # iteration on six center facelets
        cols[i]= gui_canvas.itemcget(facelet_id[i][1][1], "fill")  # colors list updated as per center facelets on schreen
    draw_cubotino()                     # updates Cubotino cube sketch, with URF centers facelets colors
    
    gui_text_window.delete(1.0, tk.END)  # clears output window
    cube_defstr=""                       # cube status string is set empty
    cube_solving_string=""               # cube solving string is set empty
    
    try:
        cube_defstr = get_definition_string()+ "\n"      # cube status string is retrieved
        if not gui_scramble_var.get():                   # case the scramble check box is not checked
            show_text(f'Cube status: {cube_defstr}\n')   # cube status string is printed on the text window
        else:                                            # case the scramble check box is checked
            show_text(f'Cube status: Random\n')          # random cube status is printed on the text window
    except:                                              # case the cube definition string is not returned 
        show_text("Invalid facelet configuration.\nWrong or missing colors.")  # feedback to user
        return  # function is terminated
    
    # Kociemba TwophaseSolver, running locally, is called with max_length=18 or timeout=2s and best found within timeout
    cube_solving_string = sv.solve(cube_defstr.strip(), 18 , 2)
    
    if cube_defstr=="":                                             # case there is no cube status string
        show_text("Invalid facelet configuration.\nWrong or missing colors.")  # feedback to user
    else:                                                           # case there is a cube status string
        if not gui_scramble_var.get():                              # case the scramble check box is not checked 
            show_text(f'Cube solution: {cube_solving_string}\n\n')  # solving string is printed on GUI text windows
        if gui_scramble_var.get():                                  # case the scramble check box is checked
            s = cube_solving_string                                 # shorter local variable name     
            s_start = s.find('(')                                   # position of open parenthesys in data
            s_end = s.find(')')                                     # position of close parenthesys in data
            manoeuvres = s[s_start+1:s_end-1]                       # cube manoeuvres are sliced from the cube solution
            show_text(f'Cube manoeuvres: {manoeuvres}\n\n')         # number of manoeuvres is printed on GUI text windows
            

        
    if not 'Error' in cube_solving_string and len(cube_solving_string)>4:   # case there is a cube to be solved
        pos=cube_solving_string.find('(')      # position of the "(" character in the string
        solution=cube_solving_string[:pos]     # string is sliced, by removing the additional info from Kociemba solver
        solution=solution.replace(" ","")      # empty spaces are removed
        
        # robot moves dictionary, and total robot moves, are retrieved from the imported Cubotino_moves script
        robot_moves_dict, robot_moves, tot_moves = cm.robot_required_moves(solution, "")
        if not gui_scramble_var.get():                       # case the scramble check box is not checked
            show_text(f'Robot moves: {robot_moves}\n')       # robot moves string is printed on the text window
        else:                                                # case the scramble check box is checked
            show_text(f'Robot moves: As per random cube\n')  # robot moves string is printed on the text window

        for key in range(len(cube_defstr.strip())):          # iteration over the cube status string
            cube_status[key]=cube_defstr[key]                # dict generation
        previous_move=0                                      # previous move set to zero

    gui_f2.update()                     # GUI f2 part is updated, to release eventual clicks on robot button
    b_robot["state"] = "active"         # GUI robot button is activated after solve() function
    b_robot["relief"] = "raised"        # GUI robot button is raised after solve() function
    gui_robot_btn_update()              # updates the cube related buttons status






def clean():
    """Restore the cube to a clean cube."""
    
    global cols, cube_solving_string
    
    cube_solving_string=""               # empty string variable to later hold the cube solution
    gui_text_window.delete(1.0, tk.END)  # clears the text window
    gui_scramble_var.set(0)
    
    cols = base_cols.copy()              # list with colors initially associated to the cube
    create_facelet_rects(width)          # cube sketch is refreshed
    
    for f in range(6):                   # iteration over the six cube faces
        for row in range(3):             # iteration over the three rows of facelets 
            for col in range(3):         # iteration over the three columns of facelets
                gui_canvas.itemconfig(facelet_id[f][row][col], fill=gui_canvas.itemcget(facelet_id[f][1][1], "fill"))
    
    draw_cubotino_center_colors()        # draw the cube center facelets with related colors, at Cubotino sketch
    gui_read_var.set("screen sketch")    # "screen sketch" activated at radiobutton, as of interest when clean()
    gui_robot_btn_update()               # updates the cube related buttons status           






def empty():
    """Remove the facelet colors except the center facelets colors."""
    
    global cols, cube_solving_string
    
    cube_solving_string=""                # empty string variable to later hold the cube solution
    gui_text_window.delete(1.0, tk.END)   # clears the text window
    
    gui_scramble_var.set(0)
    cols = base_cols.copy()              # list with colors initially associated to the cube
    create_facelet_rects(width)          # cube sketch is refreshed
    
    for f in range(6):                    # iteration over the six cube faces
        for row in range(3):              # iteration over the three rows of facelets 
            for col in range(3):          # iteration over the three columns of facelets
                if row != 1 or col != 1:  # excluded the center facelets of each face
                    gui_canvas.itemconfig(facelet_id[f][row][col], fill="grey65") # facelets are colored by gray

    draw_cubotino_center_colors()         # draw the cube center facelets with related colors, at Cubotino sketch
    gui_robot_btn_update()                # updates the cube related buttons status






def random():
    """Generate a random cube and sets the corresponding facelet colors."""
    
    global gui_read_var, cube_solving_string, cols, gui_buttons_state
    
    cube_solving_string=""                   # cube solving string is set empty
    gui_text_window.delete(1.0, tk.END)      # clears the text window
    gui_buttons_state = gui_buttons_for_cube_status("disable")   # GUI buttons (cube-status) are disabled
    
    cc = cubie.CubieCube()                   # cube in cubie reppresentation
    cc.randomize()                           # randomized cube in cubie reppresentation 
    fc = cc.to_facelet_cube()                # randomized cube is facelets reppresentation string
    
    if gui_scramble_var.get():               # case the scramble check box is checked
        cols = gray_cols.copy()              # list with gray nuances is used instead of the cube colors
    
    elif not gui_scramble_var.get():         # case the scramble check box is not checked
        cols = base_cols.copy()              # list with colors initially associated to the cube
    
    create_facelet_rects(width)              # cube sketch is refreshed to the colors 
    
    for i in range(6):                       # iteration on six center facelets
        cols[i]= gui_canvas.itemcget(facelet_id[i][1][1], "fill")  # colors list updated as center facelets on screen

    idx = 0                                  # integer index, set to zero
    for f in range(6):                       # iteration over the six cube faces
        for row in range(3):                 # iteration over the three rows of facelets 
            for col in range(3):             # iteration over the three columns of facelets

                # facelet idx, at the cube sketch, is colored as per random cube (and colors associated to the 6 faces) 
                gui_canvas.itemconfig(facelet_id[f][row][col], fill=cols[fc.f[idx]]) 
                idx += 1                     # index is increased

    redraw(str(fc))                          # cube sketch is re-freshed on GUI
    gui_read_var.set("screen sketch")        # "screen sketch" activated at radiobutton, as of interest when random()
    solve()                                  # solve function is called, because of the random() cube request
    draw_cubotino_center_colors()            # draw the cube center facelets with related colors, at Cubotino sketch
    gui_buttons_state = gui_buttons_for_cube_status("active")    # GUI buttons (cube-status) are actived






def redraw(cube_defstr):
    """Updates sketch cube colors as per cube status string."""
    
    cube_defstr=cube_defstr.strip()      # eventual empty spaces at string start/end are removed
    idx = 0                              # integer index, set to zero
    for f in range(6):                   # iteration over the six cube faces
        for row in range(3):             # iteration over the three rows of facelets 
            for col in range(3):         # iteration over the three columns of facelets
                # facelet idx, at the cube sketch, is colored as per cube_defstr in function argument
                gui_canvas.itemconfig(facelet_id[f][row][col], fill=cols[t.index(cube_defstr[idx])])
                idx += 1                 # index is increased






def click(event):
    """Define how to react on left mouse clicks."""
    
    global curcol
    
    if gui_scramble_var.get():                               # case the scramble check box is checked
        return                                               # function is returned without real actions
    
    idlist = gui_canvas.find_withtag("current")              # return the widget at pointer click
    if len(idlist) > 0:                                      # case the pointer is over a widged
        if idlist[0] in colorpick_id:                        # case the widget is one of the six color picking palette
            curcol = gui_canvas.itemcget("current", "fill")  # color selected at picking palette assigned "current color"
            for i in range(6):                               # iteration over all the six color picking palette widgets
                # the circle widget is set to thick border with same color of the GUI background
                gui_canvas.itemconfig(colorpick_id[i], width=20, outline="#F0F0F0")
            
            # the selected circle widget gets thinner borger, colored with a visible gray color
            gui_canvas.itemconfig("current", width=5, fill=curcol, outline="Grey55")
        
        elif idlist[0] not in faceletter_id:                 # case the widget is not one of the six color picking palette
            gui_canvas.itemconfig("current", fill=curcol)    # that widget is filled with the "current color"
    
    draw_cubotino_center_colors()         # draw the cube center facelets with related colors, at Cubotino sketch






def scroll(event):
    """Changes the facelets color on the schetch by scroll the mouse wheel over them."""
    
    global mainWindow_ontop, last_col, last_facelet_id
    
    
    if mainWindow_ontop:                                    # case the main windows is the one on top
        
        if gui_scramble_var.get():                          # case the scramble check box is checked
            return                                          # function is returned without real actions
    
        if len(gui_canvas.find_withtag("current"))>0:       # case scrolling over a widget
            facelet=gui_canvas.find_withtag("current")[0]   # widget id is assigned to facelet variable
            
            # case the facelet (widget id) is not a color picking and not a cube face letter
            if facelet not in colorpick_id and facelet not in faceletter_id : 
                delta = -1 if event.delta > 0 else 1        # scroll direction
                if facelet != last_facelet_id:              # case the facelet is different from the lastest one changed
                    last_col=5 if delta>0 else 0            # way to get the first color in cols list at scroll start
                    last_facelet_id=facelet                 # current facelet is asigned to the latest one changed
                
                last_col=last_col+delta                     # color number is incremented/decrement by the scroll
                last_col=last_col%6                         # scroll limited within the range of six
                gui_canvas.itemconfig("current", fill=cols[last_col]) # current facelet is filled with scrolled color

            if facelet in (5,14,23):            # case the facelet is a URF face center
                draw_cubotino_center_colors()   # draw the cube center facelets with related colors, at Cubotino sketch







def gui_buttons_for_cube_status(status):
    """Changes the button states, on those related to cube-status GUI part."""
    
    global b_read_solve, b_clean, b_empty, b_random
    
    try:
        if status == "active":                   # case the function argument is "active"
            b_read_solve["relief"] = "raised"    # button read&solve is raised
            gui_f2.update()                      # frame2 gui part is updated
        b_read_solve["state"] = status           # button read&solve activated, or disabled, according to args
        b_clean["state"] = status                # button clean activated, or disabled, according to args
        b_empty["state"] = status                # button empty activated, or disabled, according to args
        b_random["state"] = status               # button random activated, or disabled, according to args

        if status=="disable":                    # case the function argument is "disable"
            b_read_solve["relief"] = "sunken"    # button read&solve is lowered
            gui_f2.update()                      # frame2 gui part is updated
            return "disable"                     # string "disable" is returned
    except:
        return "error"
        pass






def robot_solver():
    """Sends the cube manouvres to the robot
       The solving string for the robot is without space characters, and contained within <> characters
       When the robot is working, the same button is used to stop the robot."""
    
    global cube_solving_string, cube_solving_string_robot, ser
    
    s = cube_solving_string                               # shorter local variable name
    sr = cube_solving_string_robot                        # shorter local variable name
    
    if b_robot["text"] == "Send\ndata\nto\nrobot":        # case the button is ready to send solving string to the robot
        if s != None and len(s)>1 and "f)" in s:          # case there is useful data to send to the robot
            
            sr = s.strip().strip("\r\n").replace(" ","")  # empty, CR, LF, cgaracters are removed
            if sr[0]!="<" and sr[-1:]!=">":               # case the string isn't contained by '<' and '>' characters
                sr = "<" + sr +">"                        # starting '<' and ending '>' chars are added
            cube_solving_string_robot = sr                # global variable is updated
            
            try:
                ser.write((sr+"\n").encode())             # attempt to send the solving string to the robot      
            except:
                pass
        
        else:                                             # case the cube_solving_string doesn't fit pre-conditions
            print("not a proper string...")               # feedback is printed to the terminal
        
    elif b_robot["text"] == "STOP\nROBOT":                # case the button is in stop-robot mode
        stop_robot()                                      # calls the stopping robot function
        
    gui_robot_btn_update()                                # updates the cube related buttons status
    draw_cubotino_center_colors()         # draw the cube center facelets with related colors, at Cubotino sketch






def left_Cubotino_moves(robot_moves):
    """ Generates dict with the remaining servo moves, based on the moves string.
        This is later used to keep track of the robot solving progress."""
    
    global tot_moves, left_moves
    
    left_moves={}                                       # empty dict to store the left moves 
    remaining_moves=tot_moves                           # initial remaining moves are all the moves
    for i in range(len(robot_moves)):                   # iteration over all the string characters
        if robot_moves[i]=='R' or robot_moves[i]=='S':  # case the move is cube spin or layer rotation               
            remaining_moves-=1                          # counter is decreased by one
            left_moves[i]=remaining_moves               # the left moves are associated to the move index key                           
        elif robot_moves[i]=='F':                       # case there is a flip on the move string
            remaining_moves-=int(robot_moves[i+1])      # counter is decreased by the amount of flips
            left_moves[i]=remaining_moves               # the left moves are associated to the move index key






def start_robot():
    """Function that sends the starting command to the robot. Start command is in between square brackets."""
    
    global robot_working, robot_moves
    
    if gui_scramble_var.get():                          # case the scramble check box is checked
        task = "scrambling"
    else:
        task = "solving"
    
    print("\n===========================================================================================")
    print(f"{time.ctime()}: request the robot to start {task} the cube") # print to the terminal 
    
    exception=False                                     # boolean to track the exceptions, set to false
    try:
        ser.write(("[start]\n").encode())               # attempt to send the start command to the robot
    except:
        exception=True                                  # boolean to track the exceptions is set true cause exception
        pass
    
    if not exception:                                   # case there are no exceptions
        robot_working=True                              # boolean that tracks the robot working is set True
        left_Cubotino_moves(robot_moves)                # left moves of the robot are calculated / stored
        gui_prog_bar["value"]=0                         # progress bar is set to zero
        gui_f2.update()                                 # frame2 of the gui is updated
        gui_f2.after(1000, gui_robot_btn_update())      # updates the cube related buttons status, with 1 sec delay






def stop_robot():
    """Function that sends the stopping command to the robot. Stop command is in between square brackets."""
    
    global robot_working 
    
    print("\nstopping the robot from GUI")              # print to the terminal 
    try:
        ser.write(("[stop]\n").encode())                # attempt to send the stop command to the robot
    except:
        print("\nexception raised while stopping the robot from GUI")     # print to the terminal 
        pass     
    gui_robot_btn_update()                              # updates the cube related buttons status






def gui_robot_btn_update():
    """Defines the Robot buttons state, for the robot related GUI part, according to some global variables """
                             
    global serialData, cube_solving_string, robot_working, gui_buttons_state
        
    if not robot_working:                                 # case the robot is not working
        gui_buttons_state = gui_buttons_for_cube_status("active")    # buttons for cube status are set active
        
        if not serialData:                                # case there is not serial communication set
            b_robot["relief"] = "sunken"                  # large robot button is lowered
            b_robot["state"] = "disable"                  # large robot button is disabled
            b_robot["bg"] = "gray90"                      # large robot button is gray colored
            b_robot["activebackground"] = "gray90"        # large robot button is gray colored
            if not "f)" in cube_solving_string:           # case the cube solution string has not robot moves
                b_robot["text"] = "Robot:\nNo connection\nNo data" # large robot button text, to feedback the status
            
            elif "f)" in cube_solving_string:             # case the cube solution string has not robot moves
                b_robot["text"] = "Robot:\nNot\nConnected" # large robot button text, to feedback the status
        
        # case there serial communication is set, and there are no robot moves on cube solving string
        if serialData and (not "f)" in cube_solving_string or "(0" in cube_solving_string):
            b_robot["text"] = "Robot:\nConnected\nNo data" # large robot button text, to feedback the status
            b_robot["relief"] = "sunken"                  # large robot button is lowered
            b_robot["state"] = "disable"                  # large robot button is disabled
            b_robot["bg"] = "gray90"                      # large robot button is gray colored
            b_robot["activebackground"] = "gray90"        # large robot button is gray colored
        
        # case there serial communication is set, and there are robot moves on cube solving string
        elif serialData and "f)" in cube_solving_string and not "(0" in cube_solving_string:
            b_robot["text"] = "Send\ndata\nto\nrobot"     # large robot button text, to feedback the status
            b_robot["relief"] = "raised"                  # large robot button is raised
            b_robot["state"] = "active"                   # large robot button is activated
            b_robot["bg"] = "OliveDrab1"                  # large robot button is green colored
            b_robot["activebackground"] = "OliveDrab1"    # large robot button is green colored

    if robot_working:                                     # case the robot is working
        b_robot["text"] = "STOP\nROBOT"                   # large robot button text, to feedback the status
        b_robot["relief"] = "raised"                      # large robot button is raised
        b_robot["state"] = "active"                       # large robot button is activated
        b_robot["bg"] = "orange red"                      # large robot button is red colored
        b_robot["activebackground"] = "orange red"        # large robot button is red colored
        
        if gui_buttons_state!="disable":                  # case the robot is not disabled
            gui_buttons_state = gui_buttons_for_cube_status("disable") # buttons for cube status part are disabled






def cube_facelets_permutation(cube_status, move_type, direction):
    """Function that updates the cube status, according to the move type the robot does
       The 'ref' tuples provide the facelet current reference position to be used on the updated position.
       As example, in case of flip, the resulting facelet 0 is the one currently in position 53 (ref[0])."""
    
    if move_type == 'flip':      # case the robot move is a cube flip (complete cube rotation around L-R horizontal axis) 
        ref=(53,52,51,50,49,48,47,46,45,11,14,17,10,13,16,9,12,15,0,1,2,3,4,5,6,7,8,             18,19,20,21,22,23,24,25,26,42,39,36,43,40,37,44,41,38,35,34,33,32,31,30,29,28,27)
    
    elif move_type == 'spin':    # case the robot move is a spin (complete cube rotation around vertical axis)
        if direction == '1':     # case spin is CW
            ref=(2,5,8,1,4,7,0,3,6,18,19,20,21,22,23,24,25,26,36,37,38,39,40,41,42,43,44,                33,30,27,34,31,28,35,32,29,45,46,47,48,49,50,51,52,53,9,10,11,12,13,14,15,16,17)
        elif direction == '3':      # case spin is CCW
            ref=(6,3,0,7,4,1,8,5,2,45,46,47,48,49,50,51,52,53,9,10,11,12,13,14,15,16,17,                29,32,35,28,31,34,27,30,33,18,19,20,21,22,23,24,25,26,36,37,38,39,40,41,42,43,44)
    
    elif move_type == 'rotate':  # case the robot move is a rotation (lowest layer rotation versus mid and top ones) 
        if direction == '1':     # case 1st layer rotation is CW
            ref=(0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,24,25,26,18,19,20,21,22,23,42,43,44,                33,30,27,34,31,28,35,32,29,36,37,38,39,40,41,51,52,53,45,46,47,48,49,50,15,16,17)
        elif direction == '3':   # case 1st layer rotation is CCW
            ref=(0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,51,52,53,18,19,20,21,22,23,15,16,17,                29,32,35,28,31,34,27,30,33,36,37,38,39,40,41,24,25,26,45,46,47,48,49,50,42,43,44)
    
    new_status={}                # empty dict to generate the cube status, updated according to move_type and direction
    for i in range(54):                    # iteration over the 54 facelets
        new_status[i]=cube_status[ref[i]]  # updated cube status takes the facelet from previous status at ref location
    
    return new_status                      # updated cube status is returned






def animate_cube_sketch(move_index):
    """Function that keeps updating the cube sketch colors on screen, according to the robot move."""
    
    global cube_status, robot_moves, previous_move
    
    if move_index >= previous_move or move_index==0:    # case there is a new move (or the first one)
        i=move_index                     # shorther variable name
        if robot_moves[i]=='F':          # case there is a flip on the move string
            cube_status=cube_facelets_permutation(cube_status, 'flip', None)               # cube status after a flip
            
        elif robot_moves[i]=='S':        # case there is a cube spin on the move string
            cube_status=cube_facelets_permutation(cube_status, 'spin', robot_moves[i+1])   # cube status after a spin
        
        elif robot_moves[i]=='R':        # case there is a cube 1st layer rotation
            cube_status=cube_facelets_permutation(cube_status, 'rotate', robot_moves[i+1]) # cube status after a rotate

        for k in range(54):              # iteration over the 54 facelets
            f=k//9                       # cube face
            row=(k%9)//3                 # face row
            col=(k%9)%3                  # face column
            gui_canvas.itemconfig(facelet_id[f][row][col], fill=cols[t.index(cube_status[k])])  # color filling
        
        if move_index > previous_move:   # case the move index is larger than previous (not the case on multui flips)
            previous_move +=2            # previous move index is increased (it goes with step of two)
    
    if gui_scramble_var.get():           # case the scramble check box is checked
        return                           # function is returned, by skipping Cubotino sketch update
    
    else:                                # case the scramble check box is not checked
        draw_cubotino_center_colors()    # update of center facelets colors on cube at Cubotino sketch  






def cube_read_solve():
    """GUI button retrieve the cube status from the sketch on screen, and to return the solving string."""

    global cols, gui_buttons_state    
    
    if not robot_working:                          # case the robot is not working
        gui_text_window.delete(1.0, tk.END)        # clears the text window
        gui_buttons_state = gui_buttons_for_cube_status("disable")     # disable the buttons on the cube-status GUI part
        cube_solving_string=""                     # set to empty the cube solving string
        cube_defstr=""                             # set to empty the cube status string
        var=gui_read_var.get()                     # get the radiobutton selected choice
        
        if gui_scramble_var.get():                 # case the scramble check box is checked
            gui_read_var.set("screen sketch")      # set the radiobutton to the screen sketch, as scrambling checkbutton               
        var=gui_read_var.get()                     # get the radiobutton selected choice

        if "webcam" in var:                        # case the webcam is selected as cube status detection method
            try:
                empty()                            # empties the cube sketch on screen
                cam_num = gui_webcam_num.get()     # webcam number retrieved from radiobutton
                cam_wdth = s_webcam_width.get()    # webcam width is retrieved from the slider
                cam_hght = s_webcam_height.get()   # webcam heigth is retrieved from the slider
                cam_crop = s_webcam_crop.get()     # pixels quantity to crop at the frame right side
                w_fclts = s_facelets.get()         # max number of facelets in frame width (for the contour area filter)
                
                
                webcam_cols=[]                     # empty list to be populated with the URFDLB colors sequence 
                webcam_cube_status_string=''       # string, to hold the cube status string returned by the webcam app
                
                # cube color sequence and cube status are returned via the webcam application
                webcam_cols, webcam_cube_status_string = cam.cube_status(cam_num,cam_wdth,cam_hght,cam_crop,w_fclts)

                if len(webcam_cols)==6 and len(webcam_cube_status_string)>=54:  # case the app return is valid
                    cols = webcam_cols                        # global variable URFDLB colors sequence is updated
                    cube_defstr = webcam_cube_status_string   # global variableod cube status is updated
                    cube_defstr = cube_defstr+"\n"            # cube status string in completed by '\n'
                    redraw(cube_defstr)                       # cube sketch on screen is updated to cube status string
                    draw_cubotino_center_colors()             # draw the cube center facelets with related colors
            except:
                show_text(" Cube status not defined")         # cube status undefined is printed on the text window
                pass

        elif "screen" in var:                                 # case the screen sketch is selected on the radiobuttons
            try:
                cube_defstr = get_definition_string()+"\n"    # cube status string is returned from the sketch on screen
            except:
                show_text(" Cube status not defined")         # cube status undefined is printed on the text window
                pass

        elif "robot" in var:                     # case the robot is selected on the radiobuttons
            empty()                              # empties the cube sketch on screen
            draw_cubotino_center_colors()        # draw the cube center facelets with related colors
            
        if len(cube_defstr)>=54:                 # case the cube solution string has min amount of characters
            solve()                              # solver is called
 
        draw_cubotino_center_colors()            # draw the cube center facelets with related colors
        gui_buttons_state = gui_buttons_for_cube_status("active")    # activate the buttons on the cube-status GUI part
        gui_robot_btn_update()                   # updates the cube related buttons status






def progress_percent(move_index):
    """Returns the robot solving progress, in percentage."""
    
    global tot_moves, left_moves
    
    remaining_moves= left_moves[move_index]             # remaining moves are retrived from the left moves dict
    return str(int(100*(1-remaining_moves/tot_moves)))  # returns a string with the integer of the solving percentage






def progress_update(received):
    """Function that updates the robot progress bar and the progress label
       Argument is the robot_move string index of the last move.
       As example, 'i_12', means the robot is doing the 12th move from finish."""
    
    global gui_prog_label_text, gui_prog_label
    
    if not 'end' in received:                             # case the robot is still running                    
        move_index=int(received[2:])                      # string part with the progress value
        percent=progress_percent(move_index)              # percentage is calclated
        try:
            gui_prog_bar["value"]=percent                 # progress bar is set to the percentage value
            gui_prog_label_text.set(percent+" %")         # progress label is updated with percentage value and simbol  
            if percent=="100":                            # case the solving percentage has reached 100
                gui_prog_bar["value"]='0'                 # progress bar is set to zero
                gui_prog_label_text.set("")               # progress label is set empty
        except:
            pass
    
        animate_cube_sketch(move_index)  # cube facelets sketch updates according to the robot move in execution

    elif 'end' in received:                               # case the robot has been stopped                  
        gui_prog_bar["value"]='0'                         # progress bar is set to zero
        gui_prog_label_text.set("")                       # progress label is set empty

    gui_prog_bar.update_idletasks()                       # gui widget (progress bar) is updated
    gui_prog_label.update()                               # gui widget (progress label) is updated






def robot_received_settings(received):
    """Servo settings returned by the robot."""
    
    if '(' in received and ')' in received:        # case the data contains open and close round parenthesis
        received = received.replace(' ','')        # empty spaces are removed
        data_start = received.find('(')            # position of open parenthesys in data
        data_end = received.find(')')              # position of close parenthesys in data
        print(f'servos settings sent by the robot: {received[data_start:data_end+1]}')
        data = received[data_start+1:data_end]     # data in between parenthesys is assigned, to the same string variable
        data_list=data.split(',')                  # data is split by comma, becoming a list of strings 

        settings=[]                                # empty list to store the list of numerical settings
        for setting in data_list:                  # iteration over the list of strings
            settings.append(int(setting))      # string setting changed to integer and appended to the list of settings
        
        get_settings(settings)                                 # function that updates the individual global variables
        gui_sliders_update('update_sliders')                   # function that updates the gui sliders
        with open("Cubotino_settings.txt", 'w') as f:          # open the servos setting text file in write mode
            f.write(timestamp+received[data_start:data_end+1]) # save the received servos settings

    else:                                          # case the data does not contains open and close round parenthesis
        print("not a valid settings string")       # feedback is returned






def gui_sliders_update(intent):
    """depending on the argument, this function updates the global variable based on the sliders
        or updates the sliders based on the global variables."""
    
    global robot_settings

    if intent == 'read_sliders':             # case the intention is to get sliders values to update the global variables
        robot_settings["TOP_COVER"]["ANGLE"]["FLIP"] = s_top_srv_flip.get()
        robot_settings["TOP_COVER"]["ANGLE"]["OPEN"] = s_top_srv_open.get()
        robot_settings["TOP_COVER"]["ANGLE"]["CLOSE"] = s_top_srv_close.get()
        robot_settings["TOP_COVER"]["ANGLE"]["RELEASE"] = s_top_srv_release.get()
        robot_settings["TOP_COVER"]["TIME"]["FLIP_TO_CLOSE"] = s_top_srv_flip_to_close_time.get()
        robot_settings["TOP_COVER"]["TIME"]["CLOSE_TO_FLIP"] = s_top_srv_close_to_flip_time.get()
        robot_settings["TOP_COVER"]["TIME"]["FLIP_OPEN"] = s_top_srv_flip_open_time.get()
        robot_settings["TOP_COVER"]["TIME"]["OPEN_CLOSE"] = s_top_srv_open_close_time.get()
        
        robot_settings["CUBE_HOLDER"]["ANGLE"]["CCW"]  = s_btm_srv_CCW.get()
        robot_settings["CUBE_HOLDER"]["ANGLE"]["HOME"] = s_btm_srv_home.get()
        robot_settings["CUBE_HOLDER"]["ANGLE"]["CW"] = s_btm_srv_CW.get()
        robot_settings["CUBE_HOLDER"]["ANGLE"]["EXTRA_CCW"] = s_btm_srv_extra_sides.get()
        robot_settings["CUBE_HOLDER"]["ANGLE"]["EXTRA_HOME"] = s_btm_srv_extra_home.get()
        robot_settings["CUBE_HOLDER"]["TIME"]["SPIN"] = s_btm_srv_spin_time.get()
        robot_settings["CUBE_HOLDER"]["TIME"]["ROTATE"] = s_btm_srv_rotate_time.get()
        robot_settings["CUBE_HOLDER"]["TIME"]["RELEASE"] = s_btm_srv_rel_time.get()
        

    elif intent == 'update_sliders':          # case the intention is to update sliders from the global variables values
        s_top_srv_flip.set(robot_settings["TOP_COVER"]["ANGLE"]["FLIP"])
        s_top_srv_open.set(robot_settings["TOP_COVER"]["ANGLE"]["OPEN"])
        s_top_srv_close.set(robot_settings["TOP_COVER"]["ANGLE"]["CLOSE"])
        s_top_srv_release.set(robot_settings["TOP_COVER"]["ANGLE"]["RELEASE"])
        s_top_srv_flip_to_close_time.set(robot_settings["TOP_COVER"]["TIME"]["FLIP_TO_CLOSE"])
        s_top_srv_close_to_flip_time.set(robot_settings["TOP_COVER"]["TIME"]["CLOSE_TO_FLIP"])
        s_top_srv_flip_open_time.set(robot_settings["TOP_COVER"]["TIME"]["FLIP_OPEN"])
        s_top_srv_open_close_time.set(robot_settings["TOP_COVER"]["TIME"]["OPEN_CLOSE"])
        
        s_btm_srv_CCW.set(robot_settings["CUBE_HOLDER"]["ANGLE"]["CCW"])
        s_btm_srv_home.set( robot_settings["CUBE_HOLDER"]["ANGLE"]["HOME"])
        s_btm_srv_CW.set( robot_settings["CUBE_HOLDER"]["ANGLE"]["CW"])
        s_btm_srv_extra_sides.set( robot_settings["CUBE_HOLDER"]["ANGLE"]["EXTRA_CCW"])
        s_btm_srv_extra_home.set( robot_settings["CUBE_HOLDER"]["ANGLE"]["EXTRA_HOME"])
        s_btm_srv_spin_time.set( robot_settings["CUBE_HOLDER"]["TIME"]["SPIN"])
        s_btm_srv_rotate_time.set( robot_settings["CUBE_HOLDER"]["TIME"]["ROTATE"])
        s_btm_srv_rel_time.set( robot_settings["CUBE_HOLDER"]["TIME"]["RELEASE"])






def log_data():
    """ Data logging, just for fun."""
    
    global timestamp, defStr, cube_solving_string, cube_solving_string_robot, end_method
    global tot_moves, robot_time
           

    import os                                        # os is imported to ensure the folder check/make
    folder = os.path.join('.','data_log_folder')     # folder to store the collage pictures
    if not os.path.exists(folder):                   # if case the folder does not exist
        os.makedirs(folder)                          # folder is made if it doesn't exist

    fname = folder+'\darksnake_log.txt'         # folder+filename
    
    if not os.path.exists(fname):              # case the file does not exist (file with headers is generated)
        print(f'\ngenerated \darksnake_log.txt file with headers')
        
        # columns headers
        headers = ['Date', 'CubeStatusEnteringMethod', 'CubeStatus', 'CubeSolution',
                   'RobotoMoves', 'TotCubotinoMoves', 'EndingReason', 'RobotTime(s)']
        
        s=''                                     # empty string to hold the headers, separated by tab                            
        for i, header in enumerate(headers):     # iteration over the headers list
            s+=header                            # header is added to the string
            if i < len(headers)-1:               # case there are other headers in list
                s= s+'\t'                        # tab is added to the headers string
            elif i == len(headers)-1:            # case there are no more headers in list
                s= s+'\n'                        # LF at string end

        # 'a' means the file will be generated if it does not exist, and data will be appended at the end
        with open(fname,'a') as f:               # the text file is opened in generate/edit mode
            f.write(s)                           # headers are added to the file

    
    reading_method=gui_read_var.get()            # gets the radiobutton selected choice

    # info to log
    a=str(timestamp)                             # date and time
    b=str(reading_method)                        # method used to enter the cube status
    c=str(cube_defstr.strip('\n'))               # cube status detected
    d=str(cube_solving_string.strip('n'))        # solution returned by Kociemba solver
    e=str(robot_moves)                           # robot moves string
    f=str(tot_moves)                             # total amount of Cubotino moves 
    g=str(end_method)                            # cause of the robot stop
    h=str(robot_time)                    # robot solving time (not the color reading part)
    s = a+'\t'+b+'\t'+c+'\t'+d+'\t'+e+'\t'+f+'\t'+g+'\t'+h+'\n'  # tab separated string with all the info to log

    # 'a'means the file will be generated if it does not exist, and data will be appended at the end
    fname = folder+'\darksnake_log.txt'           # folder+filename
    with open(fname,'a') as f:                   # the text file is opened in edit mode  
        f.write(s)                               # data is appended   







# ################################### IP protocol comunication related functions #############################################


def connect_check(args):
    """Function that activates the Connect button only when an IP has been selected on the drop down menu."""
    
    if "-" in clicked_ip.get():          # case no IP selected
        b_connect["state"] = "disable"   # Connect button is disabled
    else:                                # case a serial port selected
        b_connect["state"] = "active"    # Connect button is activated


def update_ips():
    """Function that updates the up running IPs connected to the current network."""
    
    global clicked_ip, b_drop_ip, ips
    
    ips = []
    threads = []

    for i in range(4):                             # Use 4 threads in checking up running host process to speed up
        threads.append(threading.Thread(target=check_ip_range, args=(64 * i, 64 * (i+1)))) 
        threads[i].start()

    for i in range(4):                             # Wait until the four threads finish
        threads[i].join()

    ips.insert(0, "-")                             # first position on drop down menu is not a serial port
    try:
        b_drop_ip.destroy()                        # previous drop down menu is destroyed
    except:
        pass
    clicked_ip = tk.StringVar()                    # string variable used by tkinter for the selection
    clicked_ip.set(ips[0])                        # activates first drop down menu position (not a serial port)
    b_drop_ip = tk.OptionMenu(gui_robot_label, clicked_ip, *ips, command=connect_check) # populated drop down menu
    b_drop_ip.config(width=11, font=("Arial", "10"))        # drop down menu settings
    b_drop_ip.grid(column=0, row=8, sticky="e", padx=10)    # drop down menu settings
    connect_check(0)                                        # updates the button Connect status
    gui_robot_btn_update()                                  # updates the cube related buttons status


def check_ip_range(start, end):
    """Function to check NodeMCU hosts up running in specific ip range."""
    global ips

    for octet in range(start, end):
        try:
            r = requests.post(f"http://192.168.1.{octet}/checkConnection", timeout=0.1)

            if r.status_code == 200:
                ips.append(f"192.168.1.{octet}")
        except:
            pass


def connection():
    """Function to open / close the serial communication.
    When a serial is opened, a thread is initiated for the communication."""
    
    global serialData, gui_prog_bar, robot_working, cube_solving_string
    
    ip = clicked_ip.get()                           # IP is retrieved from the selection made on drop down menu

    if "Disconnect" in b_connect["text"]:           # case the conection button shows Disconnect
        stop_robot()                                # robot is requested to stop
        robot_working=False                         # boolean tracking the robot working is set to False
        serialData = False                          # boolean enabling serial comm data analysis is set False
        try: 
            requests.post(f"http://{ip}/disconnect")# NodeMCU blue led is set off
        except:
            pass
        b_connect["text"] = "Connect"               # conection button label is changed to Connect
        b_refresh["state"] = "active"               # refresch com button is activated
        b_drop_ip["state"] = "active"              # drop down menu for ports is activated
        b_settings["state"] = "disable"             # settings button is disabled
        gui_robot_btn_update()                      # updates the cube related buttons status

    else:                                           # case the conection button shows Connect
        serialData = True                           # boolean enabling serial comm data analysis is set True
        gui_prog_bar["value"]=0                     # progress bar widget is set to zero
        gui_prog_bar.update_idletasks()             # progress bar widget is updated
        gui_prog_label_text.set("")                 # progress label is set to empty
        gui_prog_label.update_idletasks()           # progress label widget is updated
        gui_robot_btn_update()                      # updates the cube related buttons status
        b_connect["text"] = "Disconnect"            # conection button label is changed to Disconnect
        b_refresh["state"] = "disable"              # refresch com button is disables
        b_drop_ip["state"] = "disable"              # drop down menu for ports is disabled
        print(f"selected ip: {ip}")                 # feedback print to the terminal
        
        text_info = "Check if your PC connected to the NodeMCU network"

        try:                                        
            requests.post(f"http://{ip}/checkConnection", timeout=1)            
        except:
            if (text_info not in gui_text_window.get(1.0, tk.END)):   # case the text_info is not displayed at GUI
                show_text(f"\n{text_info}\n") # text_info is displayed at GUI
                
            serialData = False                               # boolean enabling serial comm data analysis is set True
            b_connect["text"] = "Connect"                    # conection button label is changed to Connect
            b_refresh["state"] = "active"                    # refresch com button is activated
            b_drop_ip["state"] = "active"                   # drop down menu for ports is activated
            gui_robot_btn_update()                           # updates the cube related buttons status
            
            return


        if (text_info in gui_text_window.get(1.0, tk.END)):   # case the text_info is displayed at GUI
            gui_text_window.delete(1.0, tk.END)               # clears GUI text window
            
        try:
            requests.post(f"http://{ip}/init", json=robot_settings, timeout=1)
        except:                                               # case the first write attempt goes wrong
            print("could not initialize the robot")           # feedback print to the terminal

        b_settings["state"] = "active"               # settings button is activated
            
        # t1 = threading.Thread(target=readSerial)     # a thread is associated to the readSerial function
        # t1.deamon = True                             # thread is set as deamon (runs in background with low priority)
        # t1.start()                                   # thread is started


def readSerial():
    """Functon, called by a daemon thread, that keeps reading the serial port."""
    
    global serialData, robot_working, gui_prog_bar, cube_solving_string, cube_solving_string_robot
    global end_method, robot_time
    
    while serialData and ser.isOpen():    # script has set the conditions for Serail com and serial port is found open
        try:
            data = ser.readline()                                     # serial dat is read by lines
        except:
            pass

        if len(data) > 0:                                             # case there are characters read from the serial
            try:
                received = data.decode()                              # data is decoded
                received=received.strip().strip("\n")                 # empty space and LF characters removed
            except:
                pass

            if "conn" in received:                                    # case 'conn' is in received: ESP32 is connectd
                print("established connection with ESP32\n")          # feedback is printed to the terminal


            elif "<" in received and ">" in received:                 # robot replies with the received solving string
                if received==cube_solving_string_robot.strip("\r\n"): # check if the robot received string is ok
                    start_robot()                                     # call the robot start function
                else:
                    print(f"cube_solving_string_robot received by the robot differs from :{cube_solving_string_robot}")


            elif "stop" in received and robot_working==True:          # case 'stop' is in received: Robot been stopped
                print("\nstop command received by the robot\n")       # feedback is printed to the terminal
                robot_working=False                                   # boolean trcking the robot working is set False
                end_method="stopped"                                  # variable tracking the end method
                if '(' in received and ')' in received:               # case the dat contains open and close parenthesis
                    data_start = received.find('(')                   # position of open parenthesys in received
                    data_end = received.find(')')                     # position of close parenthesys in received
                    robot_time = received[data_start+1:data_end]      # data between parenthesys is assigned
                log_data()                                            # log the more relevant data
                progress_update('i_end')                              # progress feedback is ise to end
                gui_text_window.delete(1.0, tk.END)                   # clears the text window
                cube_solving_string=""                                # cube solving string is set empty
                gui_robot_btn_update()                                # updates the cube related buttons status


            elif "start" in received:                                 # case 'start' is in received: Robot is solving
                print("start command received by the robot")          # feedback is printed to the terminal


            elif "i_" in received:                                    # case 'i_' is received: Robot progress index
                progress_update(received)                             # progress function is called


            elif "solved" in received:                                # case 'solved' is in received: Robot is solving                          
                robot_time=0.0
                robot_working=False                                   # boolean trcking the robot working is set False
                if gui_scramble_var.get():                            # case the scramble check box is checked
                    end_method="scrambled"                            # variable tracking the end method
                elif not gui_scramble_var.get():                      # case the scramble check box is not checked
                    end_method="solved"                               # variable tracking the end method
                if '(' in received and ')' in received:               # case the dat contains open and close parenthesis
                    data_start = received.find('(')                   # position of open parenthesys in received
                    data_end = received.find(')')                     # position of close parenthesys in received
                    robot_time = received[data_start+1:data_end]      # data between parenthesys is assigned
                log_data()                                            # log the more relevant data
                gui_text_window.delete(1.0, tk.END)                   # clears the text window
                cube_solving_string=""                                # cube solving string is set empty
                
                show_text(f"\n Cube {end_method} in: {robot_time} secs")  # feedback is showed on the GUI                
                print(f"\nCube {end_method}, in: {robot_time} secs")      # feedback to the terminal
                gui_robot_btn_update()                                    # updates the cube related buttons status


            elif "current_settings" in received:                      # case 'current_settings' is in received 
                print("\nservos settings request has been received by the robot")  # feedback is printed to the terminal
                robot_received_settings(received)                     # robot_received_settings function is called
            

            elif "new_settings" in received:                          # case 'new_settings' is in received 
                print("new servos settings has been received by the robot")   # feedback is printed to the terminal

            
            else:                                                     # case not expected data is received
                if data=='\n':
                    pass
                else:
                    print(f"unexpected data received by the robot: {received}") # feedback is printed to the terminal

        else:                                                 # case there not countable characters read from the serial
            if data!=b"":                                     # case the character is not an empty binary
                print(f"len data not >0")                     # feedback is printed to the terminal
                print(f"undecoded data from robot: {data}")   # feedback is printed to the terminal
                break                                         # while loop is interrupted


def close_window():
    """Function taking care to properly close things when the GUI is closed."""
    
    global root, serialData
    
    try:
        if clicked_ip.get() != "-":
            requests.post(f"http://{clicked_ip.get()}/disconnect", timeout=1)# NodeMCU blue led is set off                        # serial port (at PC) is closed
    except:
        pass
    serialData = False                             # boolean tracking serial comm conditions is set False
    root.destroy()                                 # GUI is closed






# ################################### functions to get the slider values  ##############################################

def servo_CCW(val):
    robot_settings["CUBE_HOLDER"]["ANGLE"]["CCW"] = int(val)     # bottom servo position when fully CCW

def servo_home(val):
    robot_settings["CUBE_HOLDER"]["ANGLE"]["HOME"] = int(val)          # bottom servo home position

def servo_CW(val):
    robot_settings["CUBE_HOLDER"]["ANGLE"]["CW"] = int(val)      # bottom servo position when fully CCW
    
def servo_extra_sides(val):
    robot_settings["CUBE_HOLDER"]["ANGLE"]["EXTRA_CCW"] = int(val)   # bottom servo position small rotation back from CW and CCW, to release tension
    
def servo_extra_home(val):
    robot_settings["CUBE_HOLDER"]["ANGLE"]["EXTRA_HOME"] = int(val)    # bottom servo position extra rotation at home, to releasetension

def servo_rotate_time(val):
    robot_settings["CUBE_HOLDER"]["TIME"]["ROTATE"] = int(val)   # time needed to the bottom servo to rotate about 90deg

def servo_release_time(val):
    robot_settings["CUBE_HOLDER"]["TIME"]["RELEASE"] = int(val)      # time to rotate slightly back, to release tensions

def servo_spin_time(val):
    robot_settings["CUBE_HOLDER"]["TIME"]["SPIN"] = int(val)     # time needed to the bottom servo to spin about 90deg

def servo_flip(val):
    robot_settings["TOP_COVER"]["ANGLE"]["FLIP"] = int(val)    # top servo pos to flip the cube on one of its horizontal axis

def servo_open(val):
    robot_settings["TOP_COVER"]["ANGLE"]["OPEN"] = int(val)    # top servo pos to free up the top cover from the cube

def servo_close(val):
    robot_settings["TOP_COVER"]["ANGLE"]["CLOSE"] = int(val)   # top servo pos to constrain the top cover on cube mid and top layer

def servo_release(val):
    robot_settings["TOP_COVER"]["ANGLE"]["RELEASE"] = int(val)       # top servo release position after closing toward the cube

def flip_to_close_time(val):
    robot_settings["TOP_COVER"]["TIME"]["FLIP_TO_CLOSE"] = int(val)  # time to lower the cover/flipper from flip to close position

def close_to_flip_time(val):
    robot_settings["TOP_COVER"]["TIME"]["CLOSE_TO_FLIP"] = int(val)  # time to raise the cover/flipper from close to flip position

def flip_open_time(val):
    robot_settings["TOP_COVER"]["TIME"]["FLIP_OPEN"] = int(val)      # time to raise/lower the flipper between open and flip positions

def open_close_time(val):
    robot_settings["TOP_COVER"]["TIME"]["OPEN_CLOSE"] = int(val)     # time to raise/lower the flipper between open and close positions





# ######################## functions to test the servos positions  #####################################################
def flip_cube():
    try:
        requests.post(f"http://{clicked_ip.get()}/flipTopCover", timeout=1) # send the flip_test request to the robot
    except:
        pass
    
def close_top_cover():
    try:
        requests.post(f"http://{clicked_ip.get()}/closeTopCover", timeout=1)  # send the close_cover settings request to the robot
    except:
        pass

def open_top_cover():
    try:
        requests.post(f"http://{clicked_ip.get()}/openTopCover", timeout=1) # send the open_cover settings request to the robot
    except:
        pass

def ccw():
    try:
        requests.post(f"http://{clicked_ip.get()}/rotateCounterClockwise", timeout=1)  # send the spin/rotate to CCW request to the robot
    except:
        pass
    
def home():
    try:
        requests.post(f"http://{clicked_ip.get()}/homeCubeHolder", timeout=1)  # send the spin/rotate to HOME request to the robot
    except:
        pass

def cw():
    try:
        requests.post(f"http://{clicked_ip.get()}/rotateClockwise", timeout=1)  # send the spin/rotate to CW request to the robot
    except:
        pass






# ############################ functions to get/send servos settings by/to the robot #################################

def save_robot_settings():
    """Function to save the servos settings to the json file."""
    global robot_settings
    
    try:  
        with open(ROBOT_SETTINGS_FILE, 'w') as f:
            json.dump(robot_settings, f)

        # gui_sliders_update('update_sliders')           # sliders positions are updated

    except:
        print(f"Something is wrong with {ROBOT_SETTINGS_FILE} file")






def get_current_servo_settings():
    """Request robot to send the current servos settings."""
    
    global robot_settings

    try:
        response = requests.post(f"http://{clicked_ip.get()}/getSettings", timeout=1)       # send the request to the robot for current servos settings
        robot_settings = response.json()

        gui_sliders_update('update_sliders')
    except:
        pass






def send_new_servo_settings():
    """Send new servos settings (defined via the sliders) to the robot."""
    
    global robot_settings
    
    gui_sliders_update('read_sliders')                       # sliders positions are read
                        
    try:
        requests.post(f"http://{clicked_ip.get()}/updateSettings", json=robot_settings, timeout=1)     # send the new servos settings to the robot
    except:
        pass






# ############################ functions for the webcam related settings ###############################################

def save_webcam():
    """Function to save the webcam related settings to a text file."""
    
    global timestamp
    
    cam_number=gui_webcam_num.get()     # webcam number retrieved from radiobutton
    cam_width=s_webcam_width.get()      # webcam width is retrieved from the slider
    cam_height=s_webcam_height.get()    # webcam heigth is retrieved from the slider
    cam_crop=s_webcam_crop.get()        # pixels quantity to crop at the frame right side
    facelets_in_width=s_facelets.get()  # max number of facelets in frame width (for the contour area filter)    
    
    cam_settings=(cam_number, cam_width, cam_height, cam_crop, facelets_in_width) # tuple with the settings
    data=timestamp + str(cam_settings)  # string with timestamp and string of webcam settings
    
    try: 
        with open("Cubotino_cam_settings.txt", 'w') as f:       # open the wbcam settings text file in write mode
            f.write(data)                                       # write the string and save/close the file
        print(f'\nsaving the webcam settings: {cam_settings}')  # feedback is printed to the terminal

    except:
        print("Something is wrong with Cubotino_cam_settings.txt file")


def webcam_width(val):
    cam_width = int(val)          # width of the webacam setting in pixels

def webcam_height(val):
    cam_height = int(val)         # height of the webacam setting in pixels

def webcam_crop(val):
    cam_crop = int(val)           # crop quantity of pixels to the right frame side

def facelets_width(val):
    facelets_in_width = int(val)  # min number of facelets side in frame width (to filer out too small squares)

########################################################################################################################





# ####################################################################################################################
# ############################### GUI high level part ################################################################
root = tk.Tk()                                     # initialize tkinter as root 
root.title("Dark Snake : Rubik's cube solver robot")  # name is assigned to GUI root
try:
    root.iconbitmap("Rubiks-cube.ico")             # custom icon is assigned to GUI root
except:
    pass


app_width = 12*width+40+280               # GUI width is defined via the facelet width
app_height = max(9*width+40,690)          # GUI height is defined via the facelet width, with a minimum size 670 pixels
root.minsize(app_width, app_height)       # min GUI size, that prevents resizing on screen
root.maxsize(app_width, app_height)       # max GUI size, that prevents resizing on screen

# calculate x and y coordinates for the Tk root window starting coordinate
ws = root.winfo_screenwidth()             # width of the screen
hs = root.winfo_screenheight()            # height of the screen
x = int((ws/2) - (app_width/2))           # top left x coordinate to center on the screen the GUI at its opening
y = int((hs/2) - (app_height/2))          # top left y coordinate to center on the screen the GUI at its opening


root.geometry(f'{app_width}x{app_height}+{x}+{y}') # setting the GUI dimension, and its centering to the screen

root.rowconfigure(0, weight=1)                 # root is set to have 1 row of  weight=1
root.columnconfigure(0,weight=1)               # root is set to have 1 column of weight=1

# two windows
mainWindow=tk.Frame(root)                      # a first windows (called mainWindow) is derived from root
settingWindow=tk.Frame(root)                   # a second windows (called settingWindow) is derived from root
for window in (mainWindow, settingWindow):     # iteration over the two defined windows
    window.grid(row=0,column=0,sticky='nsew')  # each window goes to the only row/column, and centered

show_window(mainWindow)                        # the first window (mainWindow) is the one that will initially appear

# the first window (mainWindow) is devided in 2 frames, a graphical one on the left and an interactibve one on the right'
gui_f1 = tk.Frame(mainWindow, width= 12 * width + 20, height= 9 * width + 40)  # first frame (gui_f1), dimensions
gui_f2 = tk.Frame(mainWindow, width= 3 * width, height= 9 * width + 40)        # second frame (gui_f2), dimensions
gui_f1.grid(row=0, column=0,sticky="ns")      # frame1 takes the left side
gui_f2.grid(row=0, column=1,sticky="ns")      # frame2 takes the right side
gui_f2.grid_rowconfigure(15, weight=1)        # frame2 uses 15 rows
gui_f2.grid_columnconfigure(0, weight=1)      # frame2 uses 1 column

# a canvas is made and positioned to fully cover frame gui_f1, in the mainWindow
gui_canvas = tk.Canvas(gui_f1, width=12*width+20, height=9*width+40, highlightthickness=0)  # gui_canvas for most of the "graphic"
gui_canvas.pack(side="top", fill="both", expand="true")   # gui_canvas is packed in gui_f1
   
root.bind("<Button-1>", click)                # pressing the left mouse button calls the click function
root.bind("<MouseWheel>", scroll)               # scrol up of the mouse wheel calls the scroll function 
########################################################################################################################






# ############################### GUI low level part ###################################################################
# ############################### Main windows widget ##################################################################

# gui text windows for feedback messages
gui_text_window = tk.Text(gui_canvas,highlightthickness=0)
gui_text_window.place(x=20+6*width+10, y=20, height=3*width-10, width=6*width-10)


# cube status and solve buttons
cube_status_label = tk.LabelFrame(gui_f2, text="Cube status", labelanchor="nw", font=("Arial", "12"))
cube_status_label.grid(column=0, row=0, columnspan=2, sticky="w", padx=10, pady=10)


# radiobuttons for cube status source
read_modes=["webcam","screen sketch"]  #,"robot color sens"]
gui_read_var = tk.StringVar()
for i, read_mode in enumerate(read_modes):
    rb=tk.Radiobutton(cube_status_label, text=read_mode, variable=gui_read_var, value=read_mode)
    rb.configure(font=("Arial", "10"))
    rb.grid(column=0, row=i, sticky="w", padx=10, pady=0)
gui_read_var.set("webcam")


# buttons for the cube status part
b_read_solve = tk.Button(cube_status_label, text="Read &\nsolve", height=3, width=11, command=cube_read_solve)
b_read_solve.configure(font=("Arial", "12"), bg="gray90", activebackground="gray90")
b_read_solve.grid(column=1, row=0, sticky="w", rowspan=3, padx=10, pady=5)

b_empty = tk.Button(cube_status_label, text="Empty", height=1, width=12, command=empty)
b_empty.configure(font=("Arial", "11"))
b_empty.grid(column=0, row=3, sticky="w", padx=10, pady=5)

b_clean = tk.Button(cube_status_label, text="Clean", height=1, width=11, command=clean)
b_clean.configure(font=("Arial", "11"))
b_clean.grid(column=1, row=3, sticky="w",padx=10, pady=5)

b_random = tk.Button(cube_status_label,text="Random", height=1, width=12, command=random)
b_random.configure(font=("Arial", "11"))
b_random.grid(column=0, row=4, padx=10, pady=10, sticky="w")

# checkbuttons for cube scrambling
gui_scramble_var = tk.BooleanVar()
cb_scramble=tk.Checkbutton(cube_status_label, text="scramble", variable=gui_scramble_var)
cb_scramble.configure(font=("Arial", "10"))
cb_scramble.grid(column=1, row=4, sticky="ew", padx=5, pady=5)
gui_scramble_var.set(0)


# robot related buttons
gui_robot_label = tk.LabelFrame(gui_f2, text="Robot", labelanchor="nw", font=("Arial", "12"))
gui_robot_label.grid(column=0, row=6, rowspan=11, columnspan=2, sticky="n", padx=10, pady=10)

b_robot = tk.Button(gui_robot_label, text="Robot", command=robot_solver, height=6, width=11)
b_robot.configure(font=("Arial", "12"), relief="sunken", state="disable")
b_robot.grid(column=1, row=7, sticky="w", rowspan=3, padx=10, pady=5)

b_refresh = tk.Button(gui_robot_label, text="Refresh IPs", height=1, width=12, command= lambda: threading.Thread(target=update_ips).start())
b_refresh.configure(font=("Arial", "11"))
b_refresh.grid(column=0, row=7, sticky="w", padx=10, pady=5) 

b_connect = tk.Button(gui_robot_label, text="Connect", height=1, width=12, state="disable", command=connection)
b_connect.configure(font=("Arial", "11"))
b_connect.grid(column=0, row=9, sticky="w", padx=10, pady=5)

gui_canvas2=tk.Canvas(gui_robot_label,width=200, height=200)  # a second canvas, for the Cubotino sketch
gui_canvas2.grid(column=0, row=11, columnspan=2, pady=5)

gui_prog_bar = ttk.Progressbar(gui_robot_label, orient="horizontal", length=175, mode="determinate")
gui_prog_bar.grid(column=0, row=12, sticky="w", padx=10, pady=10, columnspan=2)

gui_prog_label_text = tk.StringVar()
gui_prog_label = tk.Label(gui_robot_label, height=1, width=5, textvariable=gui_prog_label_text,                          font=("arial", 12), bg="#E6E6E6")
gui_prog_label.grid(column=1, sticky="e", row=12, padx=10, pady=10)

b_settings = tk.Button(gui_robot_label, text="Settings window", height=1, width=26, state="disable",
                       command= lambda: show_window(settingWindow))
b_settings.configure(font=("Arial", "11"))
b_settings.grid(column=0, row=13, columnspan=2,  padx=10, pady=5)






# ############################### Settings windows widgets #############################################################

#### general settings related widgets ####   
b_back = tk.Button(settingWindow, text="Main page", height=1, width=15, state="active",
                   command= lambda: show_window(mainWindow))
b_back.configure(font=("Arial", "11"))
b_back.grid(row=9, column=4, sticky="w", padx=20, pady=20)



#### getting and sending settings from/to the robot ####
b_get_settings = tk.Button(settingWindow, text="Get current Dark Snake settings", height=1, width=26,
                           state="active", command= get_current_servo_settings)
b_get_settings.configure(font=("Arial", "11"))
b_get_settings.grid(row=0, column=0, sticky="w", padx=20, pady=10)


b_send_settings = tk.Button(settingWindow, text="Send new settings to Dark Snake", height=1, width=26,
                           state="active", command= send_new_servo_settings)
b_send_settings.configure(font=("Arial", "11"))
b_send_settings.grid(row=0, column=1, sticky="w", padx=20, pady=10)


b_get_AF_settings = tk.Button(settingWindow, text="Save Dark Snake Settings", height=1, width=28,
                           state="active", command=save_robot_settings)
b_get_AF_settings.configure(font=("Arial", "11"))
b_get_AF_settings.grid(row=0, column=4, sticky="w", padx=20, pady=10)



#### top servo related widgets ####
top_srv_label = tk.LabelFrame(settingWindow, text="Top cover - servo settings",
                                   labelanchor="nw", font=("Arial", "12"))
top_srv_label.grid(row=1, column=0, columnspan=5, sticky="w", padx=20, pady=15)

s_top_srv_flip = tk.Scale(top_srv_label, label="Angle Flip", font=('arial','11'), orient='horizontal',
                               length=190, from_=60, to_=140, command=servo_flip)
s_top_srv_flip.grid(row=2, column=0, sticky="w", padx=12, pady=5)
s_top_srv_flip.set(robot_settings["TOP_COVER"]["ANGLE"]["FLIP"])


s_top_srv_open = tk.Scale(top_srv_label, label="Angle Open", font=('arial','11'), orient='horizontal',
                               length=190, from_=100, to_=140, command=servo_open)
s_top_srv_open.grid(row=2, column=1, sticky="w", padx=12, pady=5)
s_top_srv_open.set(robot_settings["TOP_COVER"]["ANGLE"]["OPEN"])


s_top_srv_close = tk.Scale(top_srv_label, label="Angle Close", font=('arial','11'), orient='horizontal',
                              length=190, from_=140, to_=180, command=servo_close)
s_top_srv_close.grid(row=2, column=2, sticky="w", padx=12, pady=5)
s_top_srv_close.set(robot_settings["TOP_COVER"]["ANGLE"]["CLOSE"])


s_top_srv_release = tk.Scale(top_srv_label, label="Angle release from close", font=('arial','11'), orient='horizontal',
                              length=190, from_=0, to_=5, command=servo_release)
s_top_srv_release.grid(row=2, column=3, sticky="w", padx=12, pady=5)
s_top_srv_release.set(robot_settings["TOP_COVER"]["ANGLE"]["RELEASE"])


flip_btn = tk.Button(top_srv_label, text="FLIP  (toggle)", height=1, width=20, state="active", command= flip_cube)
flip_btn.configure(font=("Arial", "12"))
flip_btn.grid(row=3, column=0, sticky="w", padx=15, pady=10)

open_btn = tk.Button(top_srv_label, text="OPEN", height=1, width=20, state="active", command= open_top_cover)
open_btn.configure(font=("Arial", "12"))
open_btn.grid(row=3, column=1, sticky="w", padx=15, pady=10)

close_btn = tk.Button(top_srv_label, text="CLOSE", height=1, width=20, state="active", command= close_top_cover)
close_btn.configure(font=("Arial", "12"))
close_btn.grid(row=3, column=2, sticky="w", padx=15, pady=10)


s_top_srv_flip_to_close_time = tk.Scale(top_srv_label, label="TIME: flip > close (ms)", font=('arial','11'),
                                        orient='horizontal', length=190, from_=100, to_=1000,
                                        resolution=50, command=flip_to_close_time)
s_top_srv_flip_to_close_time.grid(row=4, column=0, sticky="w", padx=12, pady=5)
s_top_srv_flip_to_close_time.set(robot_settings["TOP_COVER"]["TIME"]["FLIP_TO_CLOSE"])


s_top_srv_close_to_flip_time = tk.Scale(top_srv_label, label="TIME: close > flip (ms)", font=('arial','11'),
                                        orient='horizontal', length=190, from_=100, to_=1000,
                                        resolution=50, command=close_to_flip_time)
s_top_srv_close_to_flip_time.grid(row=4, column=1, sticky="w", padx=12, pady=5)
s_top_srv_close_to_flip_time.set(robot_settings["TOP_COVER"]["TIME"]["CLOSE_TO_FLIP"])


s_top_srv_flip_open_time = tk.Scale(top_srv_label, label="TIME: flip <> open (ms)", font=('arial','11'),
                                    orient='horizontal', length=190, from_=100, to_=1000,
                                    resolution=50, command=flip_open_time)
s_top_srv_flip_open_time.grid(row=4, column=2, sticky="w", padx=10, pady=5)
s_top_srv_flip_open_time.set(robot_settings["TOP_COVER"]["TIME"]["FLIP_OPEN"])


s_top_srv_open_close_time = tk.Scale(top_srv_label, label="TIME: open <> close (ms)", font=('arial','11'),
                                     orient='horizontal', length=190, from_=100, to_=700,
                                     resolution=50, command=open_close_time)
s_top_srv_open_close_time.grid(row=4, column=3, sticky="w", padx=12, pady=5)
s_top_srv_open_close_time.set(robot_settings["TOP_COVER"]["TIME"]["OPEN_CLOSE"])





#### bottom servo related widgets ####
b_srv_label = tk.LabelFrame(settingWindow, text="Cube holder - servo settings",
                                   labelanchor="nw", font=("Arial", "12"))
b_srv_label.grid(row=5, column=0, columnspan=5, sticky="w", padx=20, pady=10)


s_btm_srv_CCW = tk.Scale(b_srv_label, label="Angle CCW", font=('arial','11'), orient='horizontal',
                              length=190, from_=90, to_=180, command=servo_CCW)
s_btm_srv_CCW.grid(row=6, column=0, sticky="w", padx=13, pady=5)
s_btm_srv_CCW.set(robot_settings["CUBE_HOLDER"]["ANGLE"]["CCW"])


s_btm_srv_home = tk.Scale(b_srv_label, label="Angle home", font=('arial','11'), orient='horizontal',
                               length=190, from_=45, to_=135, command=servo_home)
s_btm_srv_home.grid(row=6, column=1, sticky="w", padx=12, pady=5)
s_btm_srv_home.set(robot_settings["CUBE_HOLDER"]["ANGLE"]["HOME"])


s_btm_srv_CW = tk.Scale(b_srv_label, label="Angle CW", font=('arial','11'), orient='horizontal',
                               length=190, from_=0, to_=90, command=servo_CW)
s_btm_srv_CW.grid(row=6, column=2, sticky="w", padx=12, pady=5)
s_btm_srv_CW.set(robot_settings["CUBE_HOLDER"]["ANGLE"]["CW"])


s_btm_srv_extra_sides = tk.Scale(b_srv_label, label="Angle release CW/CCW", font=('arial','11'), orient='horizontal',
                               length=190, from_=0, to_=10, command=servo_extra_sides)
s_btm_srv_extra_sides.grid(row=6, column=3, sticky="w", padx=12, pady=5)
s_btm_srv_extra_sides.set(robot_settings["CUBE_HOLDER"]["ANGLE"]["EXTRA_CCW"])


s_btm_srv_extra_home = tk.Scale(b_srv_label, label="Angle release at home", font=('arial','11'), orient='horizontal',
                               length=190, from_=0, to_=10, command=robot_settings["CUBE_HOLDER"]["ANGLE"]["EXTRA_HOME"])
s_btm_srv_extra_home.grid(row=6, column=4, sticky="w", padx=12, pady=5)
s_btm_srv_extra_home.set(robot_settings["CUBE_HOLDER"]["ANGLE"]["EXTRA_HOME"])


CCW_btn = tk.Button(b_srv_label, text="CCW", height=1, width=20, state="active", command= ccw)
CCW_btn.configure(font=("Arial", "12"))
CCW_btn.grid(row=7, column=0, sticky="w", padx=15, pady=10)


close_btn = tk.Button(b_srv_label, text="HOME", height=1, width=20, state="active", command= home)
close_btn.configure(font=("Arial", "12"))
close_btn.grid(row=7, column=1, sticky="w", padx=15, pady=10)


CW_btn = tk.Button(b_srv_label, text="CW", height=1, width=20, state="active", command= cw)
CW_btn.configure(font=("Arial", "12"))
CW_btn.grid(row=7, column=2, sticky="w", padx=15, pady=10)


s_btm_srv_spin_time = tk.Scale(b_srv_label, label="TIME: spin (ms)", font=('arial','11'), orient='horizontal',
                               length=190, from_=100, to_=1000,  resolution=50, command=servo_spin_time)
s_btm_srv_spin_time.grid(row=8, column=0, sticky="w", padx=12, pady=5)
s_btm_srv_spin_time.set(robot_settings["CUBE_HOLDER"]["TIME"]["SPIN"])


s_btm_srv_rotate_time = tk.Scale(b_srv_label, label="TIME: rotate (ms)", font=('arial','11'), orient='horizontal',
                               length=190, from_=100, to_=1000,  resolution=50, command=servo_rotate_time)
s_btm_srv_rotate_time.grid(row=8, column=1, sticky="w", padx=12, pady=5)
s_btm_srv_rotate_time.set(robot_settings["CUBE_HOLDER"]["TIME"]["ROTATE"])


s_btm_srv_rel_time = tk.Scale(b_srv_label, label="TIME: release (ms)", font=('arial','11'), orient='horizontal',
                               length=190, from_=0, to_=400,  resolution=50, command=servo_release_time)
s_btm_srv_rel_time.grid(row=8, column=2, sticky="w", padx=12, pady=5)
s_btm_srv_rel_time.set(robot_settings["CUBE_HOLDER"]["TIME"]["RELEASE"])



#### webcam  ####
webcam_label = tk.LabelFrame(settingWindow, text="Webcam", labelanchor="nw", font=("Arial", "12"))
webcam_label.grid(row=9, column=0, columnspan=6, sticky="w", padx=20, pady=15)

# radiobuttons for webcam source
webcam_nums=[0,1] #,2]
gui_webcam_num = tk.IntVar()
for i, webcam_num in enumerate(webcam_nums):
    rb=tk.Radiobutton(webcam_label, text=webcam_num, variable=gui_webcam_num, value=webcam_num)
    rb.configure(font=("Arial", "10"))
    rb.grid(row=10, column=0+i, sticky="w", padx=6, pady=0)
gui_webcam_num.set(cam_number)


s_webcam_width = tk.Scale(webcam_label, label="cam width", font=('arial','11'), orient='horizontal',
                               length=120, from_=640, to_=1280,  resolution=20, command=webcam_width)
s_webcam_width.grid(row=10, column=3, sticky="w", padx=15, pady=5)
s_webcam_width.set(cam_width)


s_webcam_height = tk.Scale(webcam_label, label="cam height", font=('arial','11'), orient='horizontal',
                               length=120, from_=360, to_=720,  resolution=20, command=webcam_height)
s_webcam_height.grid(row=10, column=4, sticky="w", padx=8, pady=5)
s_webcam_height.set(cam_height)


s_webcam_crop = tk.Scale(webcam_label, label="right crop", font=('arial','11'), orient='horizontal',
                               length=120, from_=0, to_=300,  resolution=20, command=webcam_crop)
s_webcam_crop.grid(row=10, column=5, sticky="w", padx=8, pady=5)
s_webcam_crop.set(cam_crop)


s_facelets = tk.Scale(webcam_label, label="distance", font=('arial','11'), orient='horizontal',
                               length=120, from_=10, to_=15,  command=facelets_width)
s_facelets.grid(row=10, column=6, sticky="w", padx=8, pady=5)
s_facelets.set(facelets_in_width)


save_cam_num_btn = tk.Button(webcam_label, text="save cam settings", height=1, width=16, state="active",
                    command= save_webcam)
save_cam_num_btn.configure(font=("Arial", "12"))
save_cam_num_btn.grid(row=10, column=8, sticky="w", padx=10, pady=10)

########################################################################################################################








# ############################### general GUI  #########################################################################

create_facelet_rects(width)                                 # calls the function to generate the cube sketch
create_colorpick(width)                                     # calls the function to generate the color-picking palette
threading.Thread(target=update_ips).start()    # calls the function to generate the cube sketch
root.protocol("WM_DELETE_WINDOW", close_window)             # the function close_function is called when the windows is closed
root.mainloop()                                             # tkinter main loop

########################################################################################################################

