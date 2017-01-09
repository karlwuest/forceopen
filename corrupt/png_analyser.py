#!/usr/bin/env python

import argparse
import os
import shutil
import sys
import struct


def main():
	# parse command line arguments
	parser = argparse.ArgumentParser(description="Analyse corrupted pngs")
	parser.add_argument('directory', metavar="DIR", type=str, help='Directory containing the corrupted pngs')
	parser.add_argument('-o', '--original-files', dest='original_files', type=str, default=None, help='Directory containing the original (uncorrupted) files for comparison (files in directory must have the same name as the corrupted version)')
	args = parser.parse_args()
	corrupted_dir = args.directory.rstrip('/')
	original_dir = args.original_files.rstrip('/')
	if os.path.isdir(corrupted_dir) and os.path.isdir(original_dir):
		for file_path in os.listdir(corrupted_dir):
			file_name = file_path.split('/')[-1]
			orig_file_path = "%s/%s" %(original_dir, file_name)
			corrupt_file_path = "%s/%s" %(corrupted_dir, file_name)
			if os.path.exists(orig_file_path) and os.path.exists(corrupt_file_path):
				analyse(corrupt_file_path, orig_file_path)
                                print # separate output for different files
	else:
		print "Invalid arguments"


def analyse(corrupt_file_path, orig_file_path):
	with open(corrupt_file_path, 'rb') as corrupt_file, open(orig_file_path, 'rb') as orig_file:
		position = 0
		corrupt_byte = corrupt_file.read(1)
		orig_byte = orig_file.read(1)
		chunk = "header"
		while corrupt_byte != '' and orig_byte != '' and position<8:
			if corrupt_byte != orig_byte:
				output(corrupt_file_path, position, chunk, position, '')
			position += 1
			corrupt_byte = corrupt_file.read(1)
			orig_byte = orig_file.read(1)
		
		while corrupt_byte != '' and orig_byte != '':
			chunk_offset = 0
			chunk = ''
			size_bin = ''
			positions = [] # store corrupted positions from chunk header
			
			# chunk length
			while corrupt_byte != '' and orig_byte != '' and chunk_offset<4:
				size_bin += orig_byte
				if corrupt_byte != orig_byte:
					positions.append((position, chunk_offset))
				position += 1
				chunk_offset += 1
				corrupt_byte = corrupt_file.read(1)
				orig_byte = orig_file.read(1)
                        chunk_size = struct.unpack('i', size_bin[::-1])[0] + 8 #length of the chunk including length and type field
                        
                        # chunk type
			while corrupt_byte != '' and orig_byte != '' and chunk_offset<8:
				chunk += orig_byte
				if corrupt_byte != orig_byte:
					positions.append((position, chunk_offset))
				position += 1
				chunk_offset += 1
				corrupt_byte = corrupt_file.read(1)
				orig_byte = orig_file.read(1)

                        
	                #print "%-30s Chunk: %s\t Chunk Size: %d" % (corrupt_file_path.split('/')[-1], chunk, chunk_size)
				
			for pos in positions:
				if pos[1] < 4:
					output(corrupt_file_path, pos[0], chunk, pos[1], "chunk length")
				else:
					output(corrupt_file_path, pos[0], chunk, pos[1], "chunk type")
					
			# chunk data
			while corrupt_byte != '' and orig_byte != '' and chunk_offset < chunk_size:
				if corrupt_byte != orig_byte:
					output(corrupt_file_path, position, chunk, chunk_offset, "chunk data")
				position += 1
				chunk_offset += 1
				corrupt_byte = corrupt_file.read(1)
				orig_byte = orig_file.read(1)
			
			# chunk CRC
			while corrupt_byte != '' and orig_byte != '' and chunk_offset < chunk_size + 4:
				if corrupt_byte != orig_byte:
					output(corrupt_file_path, position, chunk, chunk_offset, "chunk CRC")
				position += 1
				chunk_offset += 1
				corrupt_byte = corrupt_file.read(1)
				orig_byte = orig_file.read(1)
			

def output(file_path, pos, chunk, chunk_offset, field):
	file_name = file_path.split('/')[-1]
	print "%-30s Position: %d\tChunk: %s\t Chunk Offset: %d\t Field: %s" % (file_name, pos, chunk, chunk_offset, field)
if __name__ == "__main__":
    main()


