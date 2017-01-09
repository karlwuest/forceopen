#!/usr/bin/env python

import argparse
import os
import shutil
import sys
import random
from PIL import Image
import subprocess
import threading
import wnck
from time import sleep
import gtk
import signal
import resource
import psutil
import time

# pHash bindings
import pHash


scriptpath = os.path.abspath(os.path.dirname(sys.argv[0]))
pin = "%s/pin/pin" % scriptpath
branchtrace = "%s/force_open_pintools/obj-intel64/branchtrace.so" % scriptpath
hijack = "%s/force_open_pintools/obj-intel64/hijack.so" % scriptpath
display = "feh"

run_event = None
recognisable = 0

memory_usage = []

def main():
    # parse command line arguments
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Force feh to open a file")
    parser.add_argument('files', metavar="FILE", type=str, nargs='+', help='input files')
    parser.add_argument('-s', '--setup', action='store_true', default=False,
                        help='setup the branches file')
    parser.add_argument('-c', '--copy', action='store_true', default=False,
                        help='if this flag is set, files that are successfully opened are copied to "corrupted_working"')
    parser.add_argument('-a', '--auto', action='store_true', default=False,
                        help='if this flag is set, files that are forced open are closed automatically')
    parser.add_argument('-b', '--branches', dest='branches', type=str, default='branches',
                        help='file containing the branches for the instrumentation (default: ./branches)')
    parser.add_argument('-m', '--modules', dest='modules', type=str, default='modules',
                        help='file containing the modules to be instrumented (default: ./modules)')
    parser.add_argument('-o', '--original-files', dest='original_files', type=str, default=None,
                        help='Directory containing the original (uncorrupted) files for comparison (files in directory must have the same name as the corrupted version)')
    parser.add_argument('-r', '--resource-usage', dest = 'res_usage', action='store_true', default=False,
                        help='output the resource usage')
    args = parser.parse_args()
    if args.setup:
        setup(args.files, args.branches, args.modules)
    else:
        x = 0
        for f in args.files:
            if args.original_files is not None:
                correct_file = "%s/%s" % (args.original_files, f.split('/')[-1])
                if os.path.exists(correct_file):
                    ret_code = open_file3(f, args.branches, correct_file)
                else:
                    ret_code = open_file2(f, args.branches)
            elif args.auto:
                ret_code = open_file2(f, args.branches)
            else:
                ret_code = open_file(f, args.branches)
            if 0 == ret_code:
                x += 1
                if args.copy:
                    if not os.path.exists('corrupted_working_1_feh'):
                        os.makedirs('corrupted_working_1_feh')
                    shutil.copy(f, "corrupted_working_1_feh/%s" % f.split('/')[-1])
        print
        print "======================================================================"
        print
        print "Successfully opened: %d/%d" % (x, len(args.files))
        if args.original_files is not None:
            print "recognisable: %d" % recognisable
        print
        
    if args.res_usage:
        res_children = resource.getrusage(resource.RUSAGE_CHILDREN)
        res_self = resource.getrusage(resource.RUSAGE_SELF)
        # total elapsed time
        elapsed_time = time.time() - start_time
        # total cpu time
        tot_exec_time = res_children.ru_utime + res_children.ru_stime + res_self.ru_utime + res_self.ru_stime
        cpu_percent = tot_exec_time/elapsed_time * 100
        max_child_mem = max(memory_usage)/1024 # convert to KB
        # memory usage: only an estimate/upper bound (maxrss of child and self do not have to be at the same time)
        tot_max_mem = max_child_mem + res_self.ru_maxrss
        # average memory consumption
        average_mem = sum(memory_usage)/len(memory_usage)
        average_mem = average_mem/1024 # convert to KB
        # processor info
        processor = subprocess.check_output("cat /proc/cpuinfo | grep 'model name' | head -1", shell=True)
        processor = processor.split(':')[-1].strip()
        print
        print "======================================================================"
        print
        print "%-30s%s" % ("Processor: ", processor)
        print "%-30s%f s" % ("total elapsed time: ", elapsed_time)
        print "%-30s%f s" % ("total CPU time: ", tot_exec_time)
        print "%-30s%.2f" % ("CPU % (one core): ", cpu_percent)
        print "%-30s%d KB" % ("max. memory usage children: ", max_child_mem)
        print "%-30s%d KB" % ("max. memory usage total: ", tot_max_mem)
        print "%-30s%d KB" % ("average memory usage children: ", average_mem)
        print
            


def setup(files, branches_file, modules):
    """
    setup using only valid files
    """
    branches = {}
    first = True
    # named pipe for branches output
    tmp_branches = 'tmp_branches'
    if os.path.exists(tmp_branches):
        os.remove(tmp_branches)
    os.mkfifo(tmp_branches)

    for f in files:
        corrupt = False
        try:
            Image.open(f)
        except:
            corrupt = True
            #if not os.path.exists('corrupted'):
             #   os.makedirs('corrupted')
            #shutil.move(f, "corrupted/%s" % f)
        if not corrupt:
            args = [pin, "-injection", "child", "-t" , branchtrace, "-o", tmp_branches, "-m", modules, "--", display, f]
            child = subprocess.Popen(args)
            mem_thread = threading.Thread(target=mem_usage, args=(child, ))
            mem_thread.start() # record memory usage
            control_thread = threading.Thread(target=controller, args=(f.split('/')[-1],))
            control_thread.start()
            with open(tmp_branches, 'r') as cf:
                for line in cf:
                    entry = line.split(' ')
                    location = "%s %s" % (entry[0], entry[1])
                    if location in branches and branches[location] != entry[2]:
                        branches[location] = None
                    else:
                        branches[location] = entry[2]
            # wait for the child to terminate (needed for resource.rusage)
            while child.poll() is None:
                pass
            mem_thread.join()

    os.remove(tmp_branches)
    with open(branches_file, 'w') as bf:
        for key in branches.keys():
            if branches[key] != None:
                bf.write("%s %s" % (key, branches[key]))


def open_file(f, branches):
    """
    force open a file to display it
    """
    args = [pin, "-injection", "child", "-t", hijack, "-b", branches, "--", display, f]
    child = subprocess.Popen(args)
    mem_thread = threading.Thread(target=mem_usage, args=(child, ))
    mem_thread.start() # record memory usage
    ret_val = child.wait()
    mem_thread.join()
    return ret_val


def open_file2(f, branches):
    """
    force open a file and automatically close it (for testing)
    """
    args = [pin, "-injection", "child", "-t", hijack, "-b", branches, "--", display, f]
    control_thread = threading.Thread(target=controller2, args=(f.split('/')[-1],))
    control_thread.start()
    child = subprocess.Popen(args)
    mem_thread = threading.Thread(target=mem_usage, args=(child, ))
    mem_thread.start() # record memory usage
    ret_val = child.wait()
    mem_thread.join()
    if control_thread.is_alive():
        run_event.clear()
        control_thread.join()
        run_event.set()
    return ret_val


def open_file3(f, branches, correct_file):
    """
    force open a file, close it automatically and compare it to the original uncorrupted file (for testing)
    """
    args = [pin, "-injection", "child", "-t", hijack, "-b", branches, "--", display, f]
    control_thread = threading.Thread(target=controller3, args=(f.split('/')[-1], correct_file))
    control_thread.start()
    child = subprocess.Popen(args)
    mem_thread = threading.Thread(target=mem_usage, args=(child, ))
    mem_thread.start() # record memory usage
    ret_val = child.wait()
    mem_thread.join()
    if control_thread.is_alive():
        run_event.clear()
        control_thread.join()
        run_event.set()
    return ret_val



def controller(file_name):
    """
    controller for closing the files automatically in the setup phase
    """
    screen = wnck.screen_get_default()
    #for i in xrange(240):
    while run_event.is_set():
        sleep(0.5)
        #screen.force_update()
        while gtk.events_pending():
                gtk.main_iteration()
        windows = screen.get_windows()
        for w in windows:
            if file_name in w.get_name():
                print w.get_name()
                w.close(0)
                return

            
def controller2(file_name):
    """
    controller for automatically closing files after forcing them open
    if display shows its default image, or takes more than ~1 min to open a file, kill the process (no success)
    """
    screen = wnck.screen_get_default()
    i = 0
    while run_event.is_set() and i < 120:
        i += 1
        sleep(0.5)
        #screen.force_update()
        while gtk.events_pending():
                gtk.main_iteration()
        windows = screen.get_windows()
        for w in windows:
            win_name = w.get_name()
            if file_name in win_name:
                print win_name
                print "success"
                w.close(0)
                return
    if i >= 120:
        os.system("killall %s" % display)


def controller3(file_name, correct_file):
    """
    controller for automatically closing files after forcing them open and comparing the displayed picture with the original uncorrupted file
    if display shows its default image, or takes more than ~1 min to open a file, kill the process (no success)
    """
    screen = wnck.screen_get_default()
    i = 0
    while run_event.is_set() and i < 120:
        i += 1
        sleep(0.5)
        #screen.force_update()
        while gtk.events_pending():
                gtk.main_iteration()
        windows = screen.get_windows()
        for w in windows:
            win_name = w.get_name()
            if file_name in win_name:
                print win_name
                pb = screenshot(w)
                if (pb == None):
                    print "Unable to get the screenshot."
                    return
                screen = "/tmp/%s_screenshot.png" % file_name
                pb.save(screen,"png")
                w.close(0)
                
                # need to remove alpha channel of correct_file because of bug in pHash 
                try:
                    im = Image.open(correct_file)
                except:
                    print "loading correct image failed"
                    return
                im.load()
                if len(im.split()) > 3:
                    bg = Image.new("RGB", im.size, (255, 255, 255)) # new image with white background
                    bg.paste(im, mask=im.split()[3]) # paste im (masked alpha channel)
                    correct_copy = "/tmp/%s_correct.png" % file_name
                    bg.save(correct_copy, "png")
                else:
                    correct_copy = correct_file
                global recognisable
                if pHash.dct_similar(screen, correct_copy):
                    recognisable += 1
                    print "recognisable: %s" % file_name
                else:
                    print "not recognisable: %s" % file_name
                return
    if i >= 120:
        os.system("killall %s" % display)
   

def mem_usage(process):
    """
    records memory usage of process in Bytes
    """
    global memory_usage
    mem = 0
    p = psutil.Process(process.pid)
    while run_event.is_set() and not process.poll():
        try:
            temp_mem = p.get_memory_info()[0]
            for child in p.get_children(recursive=True):
                temp_mem += child.get_memory_info()[0]
        except:
            break
        if temp_mem > mem:
            mem = temp_mem
        time.sleep(0.01)
    memory_usage.append(mem)

def screenshot(window):
    win_geometry = list(window.get_client_window_geometry())
    root_win = gtk.gdk.get_default_root_window()
    pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, win_geometry[2], win_geometry[3])
    pb = pb.get_from_drawable(root_win, root_win.get_colormap(), win_geometry[0], win_geometry[1] , 0, 0, win_geometry[2], win_geometry[3])
    return pb


def signal_handler(signal, frame):
    """
    propagate SIGINT (^C) to child threads
    """
    run_event.clear()
    sys.exit(130)

if __name__ == "__main__":
    run_event = threading.Event()
    run_event.set()
    signal.signal(signal.SIGINT, signal_handler)
    main()
