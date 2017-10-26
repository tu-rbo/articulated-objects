#!/usr/bin/python

"""
Created on Wed Oct 11 17:52:55 2017

@author: Roberto Martin-Martin
"""

import os
import sys
import json
import urllib
import urllib2
import argparse
import errno 
import csv
import ntpath
import matplotlib.pyplot as mpl
import glob
import numpy as np
import re
from matplotlib import cm
import itertools
import time

if sys.version_info[0] < 3:
    import thread
else:
    import _thread
    
pause = False
end_of_seq = False
ack_end_of_seq = False

def input_thread():
    global pause, end_of_seq, ack_end_of_seq
    while not end_of_seq:
        if sys.version_info[0] < 3:
            raw_input()
        else:
            input()
        pause = not pause
        if not end_of_seq:
            if pause:
                print "Paused. Press enter again to continue"
        else:
            ack_end_of_seq = True
            print "EXIT"
    if sys.version_info[0] < 3:
        thread.exit()
    else:
        _thread.exit()

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='Script to visualize interaction data from the RBO dataset of articulated objects and interactions.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('interaction_dir', type=str,
                        help='Directory containing the raw data of the interaction')
    parser.add_argument('--rgb', action='store_true', default = False,
                        help='Visualize RGB images.')
    parser.add_argument('--d', action='store_true', default = False,
                        help='Visualize depth maps.')
    parser.add_argument('--ft', action='store_true', default = False,
                        help='Visualize force-torque signals (actuation wrenches).')
    parser.add_argument('--js', action='store_true', default = False,
                        help='Visualize joint states.')
    args = parser.parse_args()
    
    #Load data
    rgbs = sorted(glob.glob(args.interaction_dir + '/camera_rgb/*.png'))
    ds = sorted(glob.glob(args.interaction_dir + '/camera_depth_registered/*.txt'))
    
    #Find the first timestep and the time duration
    #Extract RGB times:
    rgb_times = []
    for rgb_name in rgbs:
        try:
            rgb_time = re.search('-(.+?).png', rgb_name).group(1)
        except AttributeError:
            # time not found 
            rgb_time = '' # apply your error handling
        rgb_times.append(float(rgb_time))
        
    d_times = []
    for d_name in ds:
        try:
            d_time = re.search('-(.+?).txt', d_name).group(1)
        except AttributeError:
            # time not found 
            d_time = '' # apply your error handling
        d_times.append(float(d_time))

    ft_meas = False
    ft_times = []
    ft_values = {'fx':[],'fy':[],'fz':[],'tx':[],'ty':[],'tz':[]}
    if os.path.isfile(args.interaction_dir + '/ft_sensor_netft_data.csv'):
        print "Found FT sensor measurements"
        ft_meas = True
        fts = csv.reader(open(args.interaction_dir + '/ft_sensor_netft_data.csv'))
        fts_it = fts.__iter__()
        fts_it.next()
        for ft in fts_it:
            ft_times.append(float(ft[2])/1e9)
            ft_values['fx'] += [float(ft[4])]
            ft_values['fy'] += [float(ft[5])]
            ft_values['fz'] += [float(ft[6])]
            ft_values['tx'] += [float(ft[7])]
            ft_values['ty'] += [float(ft[8])]
            ft_values['tz'] += [float(ft[9])]
    else:
        print "NOT Found FT sensor measurements"
        
    js_times = []
    js_values = {}
    jss = csv.reader(open(glob.glob(args.interaction_dir + '/*_joint_states.csv')[0]))
    js_it = jss.__iter__()
    js_first = js_it.next()
    j_idx = 4
    num_j =0
    while 'field.name' in js_first[j_idx]:
        j_idx += 1
        num_j +=1
    for js in js_it:
        js_times.append(float(js[2])/1e9)
        base_idx = 4
        base2_idx = 4 + num_j
        for idx in range(num_j):
            if js[base_idx + idx] not in js_values.keys():
                js_values[js[base_idx + idx]] = [float(js[base2_idx +idx ])]
            else:
                js_values[js[base_idx + idx]] += [float(js[base2_idx +idx ])]
    times = rgb_times + d_times + ft_times + js_times
    
    init_time = np.amin(np.array(times))
    end_time = np.amax(np.array(times))
    print "Initial time stamp: " + str(init_time)
    print "Duration of the sequence: " + str(end_time - init_time) + ' secs'
    
    #Create displays for the data
    imgs = {}
    if args.rgb:
        print "Visualizing RGB images"
        im = np.zeros([480,640])
        fig = mpl.figure()
        fig = mpl.gcf()
        fig.canvas.set_window_title('RGB')
        imgs['rgb'] = fig.figimage(im)
    if args.d:
        print "Visualizing depth maps"
        im = np.zeros([480,640])
        fig = mpl.figure()
        fig = mpl.gcf()
        fig.canvas.set_window_title('Depth')
        imgs['d'] = fig.figimage(im, cmap= mpl.get_cmap('gray'),vmin=0., vmax=3.0)
    if args.ft and ft_meas:
        print "Visualizing force-torque measurements"
        f, axarr = mpl.subplots(2, sharex=True)#, figsize=(4,3.1    ))
        fig = mpl.gcf()
        fig.canvas.set_window_title('Interaction Wrenches')
        
        imgs['f'] = axarr[0]
        axarr[0].plot([], [], 'r')
        axarr[0].plot([], [], 'g')
        axarr[0].plot([], [], 'b')
        imgs['t'] = axarr[1]
        axarr[1].plot([], [], 'r')
        axarr[1].plot([], [], 'g')
        axarr[1].plot([], [], 'b')
        axarr[0].set_xlim(init_time - init_time, end_time - init_time)
        axarr[1].set_xlim(init_time - init_time, end_time - init_time)
        #f.suptitle('Interaction Wrenches')
        f_max = np.amax(np.array(ft_values['fx'] + ft_values['fy'] + ft_values['fz']))
        f_min = np.amin(np.array(ft_values['fx'] + ft_values['fy'] + ft_values['fz']))
        axarr[0].set_ylim(f_min, f_max)
        t_max = np.amax(np.array(ft_values['tx'] + ft_values['ty'] + ft_values['tz']))
        t_min = np.amin(np.array(ft_values['tx'] + ft_values['ty'] + ft_values['tz']))
        axarr[1].set_ylim(t_min, t_max)
        axarr[0].legend(['fx','fy','fz'])
        axarr[1].legend(['tx','ty','tz'])        
        axarr[0].set_xlabel('Time [s]')
        axarr[0].set_title('Interaction Force')      
        axarr[0].set_ylabel('F [N]')
        axarr[1].set_xlabel('Time [s]')
        axarr[1].set_ylabel('T [Nm]')   
        axarr[1].set_title('Interaction Torque')       
        fig.tight_layout()   
        
    if args.js:
        print "Visualizing joint state measurements"
        fig = mpl.figure()#figsize=(4,3    ))
        fig = mpl.gcf()
        fig.canvas.set_window_title('Joint States')
        ax = fig.add_subplot(111)    
        for i in range(len(js_values.keys())):
            ax.plot([], [])
        imgs['js'] = ax        
        ax.set_xlim(init_time - init_time, end_time - init_time)        
        js_max = 0
        js_min = 0
        for js_k in js_values.keys():
            js_max = max(js_max, np.amax(np.array(js_values[js_k])))
            js_min = min(js_min, np.amin(np.array(js_values[js_k])))
            print js_k
            print np.amin(np.array(js_values[js_k]))
            print np.amax(np.array(js_values[js_k]))
        ax.set_ylim(js_min, js_max)
        print js_min
        print js_max
        ax.set_xlabel('Time [s]')
        ax.set_ylabel('Joint state [m or rad]')
        ax.legend(js_values.keys())
        ax.set_title('Joint States')
        fig.tight_layout()   
    
    #Display the data in chuncks of 1/30 secs
    prev_display_time = init_time
    display_time = init_time
    
    if sys.version_info[0] < 3:
        thread.start_new_thread(input_thread, ())
    else:
        _thread.start_new_thread(input_thread, ())
        
    print "Press enter to pause/unpause the visualization"
    global pause
    while display_time <= end_time:
        if not pause:
            img = None
            if args.rgb:
                for f in rgbs:   
                    f_time = float(re.search('-(.+?).png', f).group(1))
                    if  f_time > prev_display_time and f_time <= display_time:
                        #print f
                        im=mpl.imread(f)
                        imgs['rgb'].set_data(im)
                    elif f_time > display_time:
                        break
            if args.d:
                for f in ds:            
                    f_time = float(re.search('-(.+?).txt', f).group(1))
                    if  f_time > prev_display_time and f_time <= display_time:
                        #print f
                        im=np.loadtxt(f)
                        imgs['d'].set_data(im)
                    elif f_time > display_time:
                        break
                        
            if args.ft and ft_meas:
                new_data_x = []
                new_data_fx = []
                new_data_fy = []
                new_data_fz = []
                new_data_tx = []
                new_data_ty = []
                new_data_tz = []
                fts = csv.reader(open(args.interaction_dir + '/ft_sensor_netft_data.csv'))
                fts_it = fts.__iter__()
                fts_it.next()
                for ft in fts_it:
                    ft_time = float(ft[2])/1e9
                    if  ft_time > prev_display_time and ft_time <= display_time:
                        new_data_x += [ft_time - init_time]
                        new_data_fx += [float(ft[4])]
                        new_data_fy += [float(ft[5])]
                        new_data_fz += [float(ft[6])]
                        new_data_tx += [float(ft[7])]
                        new_data_ty += [float(ft[8])]
                        new_data_tz += [float(ft[9])]
                    elif ft_time > display_time:
                        break
                imgs['f'].lines[0].set_xdata(np.append(imgs['f'].lines[0].get_xdata(), new_data_x))
                imgs['f'].lines[0].set_ydata(np.append(imgs['f'].lines[0].get_ydata(), new_data_fx))
                imgs['f'].lines[1].set_xdata(np.append(imgs['f'].lines[1].get_xdata(), new_data_x))
                imgs['f'].lines[1].set_ydata(np.append(imgs['f'].lines[1].get_ydata(), new_data_fy))
                imgs['f'].lines[2].set_xdata(np.append(imgs['f'].lines[2].get_xdata(), new_data_x))
                imgs['f'].lines[2].set_ydata(np.append(imgs['f'].lines[2].get_ydata(), new_data_fz))
                imgs['t'].lines[0].set_xdata(np.append(imgs['t'].lines[0].get_xdata(), new_data_x))
                imgs['t'].lines[0].set_ydata(np.append(imgs['t'].lines[0].get_ydata(), new_data_tx))
                imgs['t'].lines[1].set_xdata(np.append(imgs['t'].lines[1].get_xdata(), new_data_x))
                imgs['t'].lines[1].set_ydata(np.append(imgs['t'].lines[1].get_ydata(), new_data_ty))
                imgs['t'].lines[2].set_xdata(np.append(imgs['t'].lines[2].get_xdata(), new_data_x))
                imgs['t'].lines[2].set_ydata(np.append(imgs['t'].lines[2].get_ydata(), new_data_tz))
                
            if args.js:
                for i in range(len(js_values.keys())):
                    new_data_x = []
                    new_data_y = []
                    jss = csv.reader(open(glob.glob(args.interaction_dir + '/*_joint_states.csv')[0]))
                    jss_it = jss.__iter__()
                    jss_it.next()
                    for js in jss_it:
                        js_time = float(js[2])/1e9
                        if  js_time > prev_display_time and js_time <= display_time:
                            new_data_x += [js_time - init_time] 
                            new_data_y += [float(js[4 + num_j + i])]
                        elif js_time > display_time:
                            break
                    imgs['js'].lines[i].set_xdata(np.append(imgs['js'].lines[i].get_xdata(), new_data_x))
                    imgs['js'].lines[i].set_ydata(np.append(imgs['js'].lines[i].get_ydata(), new_data_y))
                    
            
            mpl.pause(1.0/30.0)#Cannot cope with this frame rate
            mpl.draw()
            prev_display_time = display_time
            display_time += 1.0/30.0
        else:
            mpl.pause(0.5)
        
    global end_of_seq, ack_end_of_seq
    end_of_seq = True
    print "End of sequence. Press enter to end"  
    while not ack_end_of_seq:
        mpl.pause(0.5)
    exit()
