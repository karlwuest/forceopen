#!/usr/bin/env python
import sys
import os
import force_open_feh as force_open
import threading
import signal

branches_dir = "same_file_branches"

def main():
    total_files = {1:0, 2:0, 4:0, 8:0, 16:0}
    success_files = {1:0, 2:0, 4:0, 8:0, 16:0}
    recognisable = {1:0, 2:0, 4:0, 8:0, 16:0}
    if len(sys.argv) < 3:
        print "Not enough arguments"
        sys.exit(1)
    directory = sys.argv[1]
    modules = sys.argv[2]
    if not os.path.isdir(directory):
        print "%s is not a directory" % directory
        sys.exit(1)
    if not os.path.exists(branches_dir):
        os.mkdir(branches_dir)
    elif not os.path.isdir(branches_dir):
        print "%s is not a directory" % branches_dir
        sys.exit(1)
    filelist = ["%s/%s" % (directory, os.path.basename(f)) for f in os.listdir(directory)]
    for f in filelist:
        if not os.path.isdir(f):
            branches_file = "%s/%s_branches" % (branches_dir, os.path.basename(f))
            force_open.setup([f], branches_file, modules)
            for i in [1,2,4,8,16]:
                corrupted_file = "%s/corrupted%d/%s" % (os.path.dirname(f), i, os.path.basename(f))
                if not os.path.exists(corrupted_file):
                    continue
                total_files[i] += 1
                force_open.recognisable = 0
                success = force_open.open_file3(corrupted_file, branches_file, f)
                if 0==success:
                    print "Successfully opened %s" % corrupted_file
                    success_files[i] += 1
                    recognisable[i] += force_open.recognisable
                else:
                    print "Failed to open %s" % corrupted_file
            # train with file
            # force open the according file in corrupted{1,2,4,8,16}
            # output results
    print 
    print "======================================================================"
    print
    print "RESULTS"
    for i in [1,2,4,8,16]:
        print
        print "======================================================================"
        print "corrupted%d:" % i
        print "total:\t%d" % total_files[i]
        print "opened:\t%d" % success_files[i]
        print "recognisable:\t%d" % recognisable[i]
        
    

if __name__ == "__main__":
    force_open.run_event = threading.Event()
    force_open.run_event.set()
    signal.signal(signal.SIGINT, force_open.signal_handler)
    main()
