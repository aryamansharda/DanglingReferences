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

def extract_ib_outlets_from_table_view_cell(view_controller):
	table_view_cells = view_controller.findall('.//tableViewCell')
	table_view_cell_to_ib_outlet_map = {}

	for table_view_cell in table_view_cells:
		table_view_cells_connections = table_view_cell.findall('./connections/')

		ib_outlets = [connection.attrib["property"] for connection in table_view_cells_connections if connection.tag == "outlet" or connection.tag == "outletCollection"]

		if "customClass" in table_view_cell.attrib:
			table_view_cell_to_ib_outlet_map[table_view_cell.attrib["customClass"]] = set(ib_outlets)
	return table_view_cell_to_ib_outlet_map

def extract_ib_outlets_from_collection_view_cell(view_controller):
	collection_view_cells = view_controller.findall('.//collectionViewCell')
	collection_view_cell_to_ib_outlet_map = {}

	for collection_view_cell in collection_view_cells:
		collection_view_cells_connections = collection_view_cell.findall('./connections/')

		ib_outlets = [connection.attrib["property"] for connection in collection_view_cells_connections if connection.tag == "outlet" or connection.tag == "outletCollection"]

		if "customClass" in collection_view_cell.attrib:
			collection_view_cell_to_ib_outlet_map[collection_view_cell.attrib["customClass"]] = set(ib_outlets)
	return collection_view_cell_to_ib_outlet_map

def load_ib_outlets_from_storyboards():
	storyboard_ib_outlet_map = {}	
	table_view_cell_to_ib_outlet_map = {}
	collection_view_cell_to_ib_outlet_map = {}

	# Split into .storyboard and .swift files
	storyboards = findAllFilesWithExtension("/Users/aryamansharda/Documents/bowman/Bowman", ".storyboard")

	for storyboard in storyboards:
		tree = ET.parse(storyboard)
		root = tree.getroot()

		viewControllers = root.findall('.//viewController')
		for viewController in viewControllers:
			# If there is no customClass provided, then there can't be a ViewController hence no IBOutlets to check for
			if "customClass" in viewController.attrib:
				view_controller_class_name = viewController.attrib["customClass"]
				
				connections = viewController.findall('./connections/')
				view_controllers_ib_outlets = [connection.attrib["property"] for connection in connections if connection.tag == "outlet" or connection.tag == "outletCollection"]
				storyboard_ib_outlet_map[view_controller_class_name] = set(view_controllers_ib_outlets)

				# Collect all of the cells identified on this page. We'll need to validate them later
				table_view_cell_to_ib_outlet_map.update(extract_ib_outlets_from_table_view_cell(viewController))
				collection_view_cell_to_ib_outlet_map.update(extract_ib_outlets_from_collection_view_cell(viewController))
										
	return storyboard_ib_outlet_map, table_view_cell_to_ib_outlet_map, collection_view_cell_to_ib_outlet_map

def load_ib_outlets_from_objective_c_source():
	objc_files = findAllFilesWithExtension("/Users/aryamansharda/Documents/bowman/Bowman", ".h") + findAllFilesWithExtension("/Users/aryamansharda/Documents/bowman/Bowman", ".m")

	source_to_ib_outlet_mapping = {}
	subclass_to_parent_mapping = {}

	for source in objc_files:
		# Retrieves just the view controller's name
		source_file_name = Path(source).stem
		# print(source_file_name)

		with open(source, 'r') as file:

			try:	
				fileContents = file.read()			

				allIBOutlets = re.findall('\\sIBOutlet.*\\*\\s*(.*);', fileContents)
				# print(allIBOutlets)
					
				if source_file_name in source_to_ib_outlet_mapping:
					source_to_ib_outlet_mapping[source_file_name] += allIBOutlets
				else:
					source_to_ib_outlet_mapping[source_file_name] = allIBOutlets

				# Create a relationship between all of the base and derived classes as this may be needed later on			
				parentClasses = []

				# print(Path(source).suffix)
				if ".h" in source:
					parentClasses = re.findall('@interface\\s+\\w+\\s+:\\s+(\\w+)', fileContents)

					print("Finding parents")			
					print(parentClasses)
					
					if parentClasses:
						subclass_to_parent_mapping[source_file_name] = parentClasses[0].split(' ')[-1]
						# print("Parents: " + str(parentClasses[0].split(' ')[-1]))
			except:
				print("Failed to process file: " + source_file_name)

	return source_to_ib_outlet_mapping, subclass_to_parent_mapping

def load_ib_outlets_from_swift_source():
	# Find a matching .swift file and extract the IBOutlets
	swiftSourceFiles = findAllFilesWithExtension("/Users/aryamansharda/Documents/bowman/Bowman", ".swift")

	source_to_ib_outlet_mapping = {}
	swift_subclass_to_parent_mapping = {}

	for source in swiftSourceFiles:
		# Retrieves just the view controller's name
		source_file_name = Path(source).stem
		with open(source, 'r') as file:

			fileContents = file.read()
			print(source_file_name)

			# Gets all IBOutlets with optionality \\s@IBOutlet.*.var\\s(.*):.*!
			allIBOutlets = re.findall('\\s@IBOutlet.*.var\\s(.*):', fileContents)
			print(allIBOutlets)
			parentClasses = re.findall(source_file_name + ':.(.*.){', fileContents)

			source_to_ib_outlet_mapping[source_file_name] = set(allIBOutlets)

			# Create a relationship between all of the base and derived classes as this may be needed later on
			if parentClasses:
				swift_subclass_to_parent_mapping[source_file_name] = parentClasses[0].split(',')

	return source_to_ib_outlet_mapping, swift_subclass_to_parent_mapping

def find_ib_outlets_in_parent_class(swift_source_ib_outlet_map, subclass_to_parent_mapping, current_child_view_controller):
	parents_ib_outlets = []

	try:
		parent_classes = subclass_to_parent_mapping[current_child_view_controller]

		for potential_parent in parent_classes:
			potential_parent = potential_parent.strip()

			if potential_parent in swift_source_ib_outlet_map:
				parents_ib_outlets += swift_source_ib_outlet_map[potential_parent]
	except:
		print("")
		# Key error on: " + current_child_view_controller)
	
	return set(parents_ib_outlets)

def validate_ib_outlet_connections(ib_outlet_map):	
	failures = 0
	for key, value in ib_outlet_map.items():
		logger.info("Processing " + key + "...")

		if key in all_ib_outlet_map:
			outlets_defined_in_parent_class = set(find_ib_outlets_in_parent_class(all_ib_outlet_map, subclass_to_parent_mapping, key))
			outlets_defined_in_code = set(all_ib_outlet_map[key])
			outlets_from_storyboard = value

			result = set()

			# print(outlets_defined_in_code)
			# print(outlets_from_storyboard)

			if len(outlets_defined_in_code) >= len(outlets_from_storyboard):
				result = outlets_defined_in_code - outlets_from_storyboard
			else:
				result = outlets_from_storyboard - outlets_defined_in_code

			if len(result) > 0:
				if len(result) >= len(outlets_defined_in_parent_class):
					result = result - outlets_defined_in_parent_class
				else:
					# The parent can always contain additional 
					result = outlets_defined_in_parent_class - result
			
			# At this point there are some remaining unaccounted for IBOutlets
			# Either these all exist in the parent class and the child class is only making a few of the connections and inheritint the rest
			# or the child class contains an extra IBOutlet reference that isn't inherited or has parity between the code and the storyboard
			# which would imply an error
			# 
			# TLDR: Checking if the child is inheriting the unaccounted for IBOutlets from it's parent. Otherwise, we've found a real error.
			if len(result) > 0 and not result.issubset(outlets_defined_in_parent_class):
				failures += 1		
				logger.critical("Failure: " + str(result))
		else:
			logger.warning("Key not found in mapping. Assuming ObjC file or error.")

	print("Failures: " + str(failures))

objc_source_ib_outlet_map, objc_subclass_to_parent_mapping = load_ib_outlets_from_objective_c_source()
view_controllers_ib_outlet_map, table_view_cell_to_ib_outlet_map, collection_view_cell_to_ib_outlet_map = load_ib_outlets_from_storyboards()
swift_source_ib_outlet_map, swift_subclass_to_parent_mapping = load_ib_outlets_from_swift_source()

print("Output:")
print(swift_source_ib_outlet_map)

# Combine ObjC & Swift child parent relationships into one dictionary
subclass_to_parent_mapping = {}
subclass_to_parent_mapping = objc_subclass_to_parent_mapping.copy()
subclass_to_parent_mapping.update(swift_subclass_to_parent_mapping)

# Combine ObjC & Swift IBOutlet declarations into one dictionary
all_ib_outlet_map = objc_source_ib_outlet_map.copy()
all_ib_outlet_map.update(swift_source_ib_outlet_map)

validate_ib_outlet_connections(view_controllers_ib_outlet_map)
validate_ib_outlet_connections(table_view_cell_to_ib_outlet_map)
validate_ib_outlet_connections(collection_view_cell_to_ib_outlet_map)
