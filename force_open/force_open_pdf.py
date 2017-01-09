#!/usr/bin/env python

import argparse
import os
import shutil
import sys
import random
import subprocess
import threading
from time import sleep
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
display = "pdftotext"

run_event = None
recognisable = 0

memory_usage = []

def main():
    # parse command line arguments
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Force pdftotext to open a file")
    parser.add_argument('files', metavar="FILE", type=str, nargs='+', help='input files')
    parser.add_argument('-s', '--setup', action='store_true', default=False,
                        help='setup the branches file')
    parser.add_argument('-c', '--copy', action='store_true', default=False,
                        help='if this flag is set, files that are successfully opened are copied to "corrupted_working"')
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
            else:
                ret_code = open_file(f, args.branches)
            if 0 == ret_code:
                x += 1
                if args.copy:
                    if not os.path.exists('corrupted_working_pdf'):
                        os.makedirs('corrupted_working_pdf')
                    shutil.copy(f, "corrupted_working_pdf/%s" % f.split('/')[-1])
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
        args = [pin, "-injection", "child", "-t" , branchtrace, "-o", tmp_branches, "-m", modules, "--", display, f]
        child = subprocess.Popen(args)
        mem_thread = threading.Thread(target=mem_usage, args=(child, ))
        mem_thread.start() # record memory usage
        with open(tmp_branches, 'r') as cf:
            for line in cf:
                entry = line.split(' ')
                location = "%s %s" % (entry[0], entry[1])
                if location in branches and branches[location] != entry[2]:
                    branches[location] = None
                else:
                    branches[location] = entry[2]
        # wait for the child to terminate (needed for resource.rusage)
        child.wait()
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
    child = subprocess.Popen(args)
    mem_thread = threading.Thread(target=mem_usage, args=(child, ))
    mem_thread.start() # record memory usage
    # kill process if it takes more than 1 min
    i = 0
    ret_val = child.poll()
    while ret_val is None and i <120:
        sleep(0.5)
        ret_val = child.poll()
        i += 1
    if ret_val is None:
        os.system("killall -9 %s" % display)
	#child.kill()
	#os.killpg(child.pid, 9)
        ret_val = child.poll()
    mem_thread.join()
    return ret_val


def open_file3(f, branches, correct_file):
    """
    force open a file, close it automatically and compare it to the original uncorrupted file (for testing)
    """
    txt_name = os.path.splitext(f)[0] + '.txt'
    if os.path.exists(txt_name):
        os.remove(txt_name)
    args = [pin, "-injection", "child", "-t", hijack, "-b", branches, "--", display, f]
    child = subprocess.Popen(args)
    mem_thread = threading.Thread(target=mem_usage, args=(child, ))
    mem_thread.start() # record memory usage
    # kill process if it takes more than 1 min
    i = 0
    ret_val = child.poll()
    while ret_val is None and i <120:
        sleep(0.5)
        ret_val = child.poll()
        i += 1
    if ret_val is None:
        os.system("killall -9 %s" % display)
	#child.kill()
	#os.killpg(child.pid, 9)
        ret_val = child.poll()
    if ret_val == 0 and os.path.exists(txt_name):
        correct_text = os.path.splitext(correct_file)[0] + '.txt'
        if not os.path.exists(correct_text):
            args = [display, correct_file]
            subprocess.call(args)
        with open(txt_name) as txt_file:
            str1 = txt_file.read()
        with open(correct_text) as correct_txt_file:
            str2 = correct_txt_file.read()
        dist = levenshtein(str1, str2)
        print "Sucess: File %s\t correct txt length: %d \t edit distance: %d \t ratio: %f " % (f, len(str2), dist, float(dist)/len(str2))
    else:
        print "Failure: File %s could not be reconstructed" % f
    mem_thread.join()
    return ret_val

def levenshtein(str1, str2):
    if str1 == str2:
        return 0
    if len(str2) > len(str1):
        str1, str2 = str2, str1
    new_distance = [0]*(len(str2) + 1)
    distance =  [0]*(len(str2) + 1)
    for j in xrange(len(str2) + 1):
        distance[j] = j
    for i in xrange(1, len(str1) + 1):
        new_distance[0] = i
        for j in xrange(1, len(str2) + 1):
            dist1 = distance[j] + 1
            dist2 = new_distance[j-1] + 1
            dist3 = distance[j-1]
            if str1[i-1] != str2[j-1]:
                dist3 += 1
            new_distance[j] = min(dist1, dist2, dist3)
        new_distance, distance = distance, new_distance

    return distance[len(str2)]
   

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
