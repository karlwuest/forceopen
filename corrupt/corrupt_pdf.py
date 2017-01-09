#!/usr/bin/env python

import argparse
import os
import shutil
import sys
import random
#import PythonMagick
import subprocess
from time import sleep
#from pyPdf import PdfFileReader

def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(description="Corrupt files")
    parser.add_argument('files', metavar="FILE", type=str, nargs='+', help='a file to corrupt')#, dest='files')
    parser.add_argument('-n','--number-of-bytes', dest='num_bytes', type=int, default=1,
                      help="the number of bytes that will be corrupted (default: 1")
    parser.add_argument('-o','--output-directory', dest='out_dir', type=str, default='corrupted',
                      help="the directory to store the corrupted files (default: ./corrupted)")
    parser.add_argument('-o2','--output-directory2', dest='out_dir2', type=str, default='uncorrupted',
                      help="the directory to store the uncorrupted files (default: ./uncorrupted)")
    args = parser.parse_args()
    corrupt_files(args.files, args.out_dir, args.num_bytes, args.out_dir2)

def corrupt_files(files, out_dir, num_bytes, out_dir2):
    """
    corrupts the files listed in 'files' in 'num_bytes' bytes, corrupted files are stored in 'out_dir'
    does not have a success rate of 100% due to random position of corrupted byte(s)
    """
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    if not os.path.exists(out_dir2):
        os.makedirs(out_dir2)
    for in_file in files:
        if os.path.isfile(in_file):
            out_file = "%s/%s" % (out_dir, in_file.split('/')[-1])
            corrupted = False
            i = 0
            # limit to 'max_it' iterations to prevent extremely long runtime
            max_it = 1000
            if os.path.exists(out_file):
                i = max_it
            #if out_file.endswith("pdf"): # pdf takes longer per iteration
            #    max_it = 100
            while i < max_it:
                i += 1
                shutil.copy(in_file, out_file)
                file_size = os.path.getsize(out_file)
                pos = random.randint(0, file_size-num_bytes)
                print "Pos = %d" % pos
                
                # corrupt the file
                with open(out_file, 'r+') as f:
                    f.seek(pos)
                    f.write(os.urandom(num_bytes))
                # check if we can open the file
                with open("/dev/null", 'w') as null:
                    if subprocess.call(["pdftotext", out_file], stdout=null):
                        break
                #child = subprocess.Popen(["okular", out_file])
                #sleep(0.4)
                #if child.poll():
                #    break
                #else:
                #    child.terminate()
                #try:
                #    PdfFileReader(file(out_file, "rb"))
                #except:
                #    break
                
            else:
                # File could not be corrupted
                print "Could not make unreadable: %s" % in_file
                os.remove(out_file)
                shutil.copy(in_file, "%s/%s" % (out_dir2, in_file.split('/')[-1]))
        else:
            print >> sys.stderr, "file does not exist: %s" % in_file


if __name__ == "__main__":
    main()
