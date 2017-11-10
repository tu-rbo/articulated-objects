#!/usr/bin/python

import csv
import rospkg
import argparse
import subprocess
import signal
from sys import exit
from os.path import join
from time import sleep

def start_rviz(use_ft):
	if use_ft:
		pcall = ["rviz", "-d", join(PACKAGE_PATH, "cfg", "visualize_recording_ft.rviz")]
	else:
		pcall = ["rviz", "-d", join(PACKAGE_PATH, "cfg", "visualize_recording.rviz")]
	return subprocess.Popen(pcall)

def play_rosbag(found_row, bagname):
	pcall = ["roslaunch", 
		"articulated_objects_db", 
		"play_recording.launch", 
		"object:=" + found_row["Object"],
		"bag:=" + bagname,
		"config:=configuration_" + found_row["recording date(marker set id)"],
		"ftSensor:=" + found_row["force/torque sensor used"]
	]
	return subprocess.Popen(pcall)

def create_shutdown_handler(procs):
	def shutdown_handler(signum, frame):
		for p in procs:
			if p.poll() == None:
				p.terminate()
		print("Wait for processes to terminate...")
		sleep(1.5)
		for i, p in enumerate(procs):
			if p.poll() == None:
				print(str(i) + ': ' + str(p) + " did not terminate in time. Escalating to SIGKILL")
				p.kill()
		exit()
	return shutdown_handler	


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Convience script to play a recorded rosbag in the articulated objects db')
	parser.add_argument('bag', type=str,
		            help='the file name of the recording (e.g. pliers01_o.bag)')

	parser.add_argument('-p', '--norosplay', action='store_true',
		            help='if set no rosbag will be played')

	parser.add_argument('-v', '--norviz', action='store_true',
		            help='if set rviz will not be started')

	args = parser.parse_args()

	rospack = rospkg.RosPack()
	PACKAGE_PATH = rospack.get_path('articulated_objects_db')

	interaction_name = args.bag
	if args.bag.endswith("_o.bag"):
		interaction_name = args.bag[:-6]
	elif args.bag.endswith(".bag"):
		print("[ERROR] The rosbag has to contain the joint states (ends with _o.bag)")
		exit()
		#interaction_name = args.bag[:-4]

	#read out csv file and find correct config information  
	found = False
	with open(join(PACKAGE_PATH, "data", "interactions", 'interactions_index.csv')) as csvfile:
		reader = csv.DictReader(csvfile)

		found_row = None
		for row in reader:
			if(row["Name"] == interaction_name):
				found_row = row
				break

	# try to start the actual visualization
	if found_row:

		procs = []
		if not args.norviz:
			procs.append(start_rviz(found_row["force/torque sensor used"] == '1'))

		if not args.norosplay:
			procs.append(play_rosbag(found_row, args.bag))

		if procs:
			signal.signal(signal.SIGINT, create_shutdown_handler(procs))
			while True:
				rviz_process = procs[0]
				if not args.norviz and not rviz_process.poll() == None:
					create_shutdown_handler(procs[1:])(None, None)
				sleep(0.1)
		else:			
			print("Found entry for " + args.bag + " in the interaction index, but nothing was started. You provided all ignore flags to the script!")
	else:
		print(args.bag + " was not found in the interaction index")



