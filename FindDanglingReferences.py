import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import coloredlogs, logging

# Setting up logger
logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)

# Find all files matching an extension
def findAllFilesWithExtension(path, extension):
	files = []

	for r, d, f in os.walk(path):
	    for file in f:
	        if extension in file:
	            files.append(os.path.join(r, file))
	return files


def load_ib_outlets_from_storyboards():
	storyboard_ib_outlet_map = {}

	# Split into .storyboard and .swift files
	storyboards = findAllFilesWithExtension("/Users/aryamansharda/Documents/bowman/Bowman", ".storyboard")

	for storyboard in storyboards:
		tree = ET.parse(storyboard)
		root = tree.getroot()

		viewControllers = root.findall('.//viewController')
		for viewController in viewControllers:
			# TODO: Handle rootViewControllers -> ModifyTrip -> New charges
			if "customClass" in viewController.attrib:
				view_controller_class_name = viewController.attrib["customClass"]

				connections = viewController.findall('.//connections/*')
				ib_outlets = [connection.attrib["property"] for connection in connections if connection.tag == "outlet"]

				storyboard_ib_outlet_map[view_controller_class_name] = ib_outlets
			
			# 	# TODO: See if there are any other types besides selector
			# 	print("IBAction found: " + connection.attrib["selector"])
	return storyboard_ib_outlet_map

def load_ib_outlets_from_swift_source():
	# Find a matching .swift file and extract the IBOutlets
	swiftSourceFiles = findAllFilesWithExtension("/Users/aryamansharda/Documents/bowman/Bowman", ".swift")

	# Only process ViewController Swift files
	# TODO: I don't think is necessary if we're going to handle cells too
	# swiftSourceFiles = [source for source in swiftSourceFiles if "ViewController.swift" in source]

	source_to_ib_outlet_mapping = {}
	subclass_to_parent_mapping = {}

	for source in swiftSourceFiles:
		# Retrieves just the view controller's name
		source_file_name = Path(source).stem

		with open(source, 'r') as file:

			fileContents = file.read()			
			allIBOutlets = re.findall('\\s@IBOutlet.*.var\\s(.*):', fileContents)
			parentClasses = re.findall(source_file_name + ':.(.*.){', fileContents)

			source_to_ib_outlet_mapping[source_file_name] = allIBOutlets

			# Create a relationship between all of the base and derived classes as this may be needed later on
			if parentClasses:
				subclass_to_parent_mapping[source_file_name] = parentClasses[0].split(',')

	return source_to_ib_outlet_mapping, subclass_to_parent_mapping

def find_ib_outlets_in_parent_class(swift_source_ib_outlet_map, subclass_to_parent_mapping):
	parents_ib_outlets = []

	# Adds the parents IBOutlet's to the child's IBOutlet
	for child, parent_classes in subclass_to_parent_mapping.items():		

		for potential_parent in parent_classes:
			if potential_parent in swift_source_ib_outlet_map:
				parents_ib_outlets += swift_source_ib_outlet_map[potential_parent]
		
	return parents_ib_outlets

logger.info("Processing storyboard files")
storyboard_ib_outlet_map = load_ib_outlets_from_storyboards()

logger.info("Processing .swift files")
swift_source_ib_outlet_map, subclass_to_parent_mapping = load_ib_outlets_from_swift_source()

failures = 0

for key, value in storyboard_ib_outlet_map.items():
	# TODO: This approach only handles Swift currently - remember that

	logger.info("Processing " + key + "...")

	if key in swift_source_ib_outlet_map:		
		print("IBOutlets: " + str(set(value)))
		print("Code References: " + str(set(swift_source_ib_outlet_map[key])))

		# HostCleaningChecklistViewController 
		result = set(value).difference(set(swift_source_ib_outlet_map[key])) 
		print(str(result))

		if result:
			logger.warning("Found some missing properties. Checking for declaration in parent class.")
		
			# print('The missing properties may be in the parent class: ' + str(subclass_to_parent_mapping[key]))
			# print("Checking parent classes for IBOutlet / IBAction declarations:")
			# print("Currently missing: " + str(remaining_ib_outlets))

			parents_ib_outlets = find_ib_outlets_in_parent_class(swift_source_ib_outlet_map, subclass_to_parent_mapping)
			print("parents_ib_outlets: " + str(parents_ib_outlets))
			remaining_ib_outlets = result - set(parents_ib_outlets)

			if remaining_ib_outlets:
				failures += 1
				logger.critical("Could not find the following connections: " + str(remaining_ib_outlets))
			else:
				logger.info("All IBOutlet references found.")
			

if failures == 0:
	logger.debug("No dangling IBOutlet references found.")
else:
	logger.critical("Dangling IBOutlet references were found - please see logs.")


# Edge Cases
# 2 Swift VCs with the same name, but different file paths - this is because I'm just saving the last part of the filepath for the Swift extension
# 2 VCs declared in the same file

# Fails on:
# Prototype cells
# Subclasses - if one VC is a subclass of another VC, just add the parent VCs outlets to this one

# TODO: .xib & IBActions
