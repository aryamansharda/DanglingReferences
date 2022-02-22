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
			print("Processing.." + table_view_cell.attrib["customClass"] + "with parent VC: " + view_controller.attrib["customClass"])

			table_view_cell_to_ib_outlet_map[table_view_cell.attrib["customClass"]] = set(ib_outlets)
	return table_view_cell_to_ib_outlet_map

def extract_ib_outlets_from_collection_view_cell(view_controller):
	collection_view_cells = view_controller.findall('.//collectionViewCell')
	collection_view_cell_to_ib_outlet_map = {}

	for collection_view_cell in collection_view_cells:
		collection_view_cells_connections = collection_view_cell.findall('./connections/')

		ib_outlets = [connection.attrib["property"] for connection in collection_view_cells_connections if connection.tag == "outlet" or connection.tag == "outletCollection"]

		if "customClass" in collection_view_cell.attrib:
			print("Processing.." + collection_view_cell.attrib["customClass"] + "with parent VC: " + view_controller.attrib["customClass"])

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
				# print(view_controller_class_name)

				# Mapping the view controller's custom class name to just the IBOutlets declared on the storyboard representation of the view controller
				connections = viewController.findall('./connections/')
				view_controllers_ib_outlets = [connection.attrib["property"] for connection in connections if connection.tag == "outlet" or connection.tag == "outletCollection"]
				storyboard_ib_outlet_map[view_controller_class_name] = set(view_controllers_ib_outlets)

				# Collect all of the cells identified on this page. We'll need to validate them later
				table_view_cell_to_ib_outlet_map.update(extract_ib_outlets_from_table_view_cell(viewController))
				collection_view_cell_to_ib_outlet_map.update(extract_ib_outlets_from_collection_view_cell(viewController))
							
			# 	# TODO: See if there are any other types besides selector
			# 	print("IBAction found: " + connection.attrib["selector"])
	
	return storyboard_ib_outlet_map, table_view_cell_to_ib_outlet_map, collection_view_cell_to_ib_outlet_map


def load_ib_outlets_from_swift_source():
	# Find a matching .swift file and extract the IBOutlets
	swiftSourceFiles = findAllFilesWithExtension("/Users/aryamansharda/Documents/bowman/Bowman", ".swift")

	source_to_ib_outlet_mapping = {}
	subclass_to_parent_mapping = {}

	for source in swiftSourceFiles:
		# Retrieves just the view controller's name
		source_file_name = Path(source).stem
		with open(source, 'r') as file:

			fileContents = file.read()			

			# Gets all IBOutlets with optionality \\s@IBOutlet.*.var\\s(.*):.*!
			allIBOutlets = re.findall('\\s@IBOutlet.*.var\\s(.*):', fileContents)
			parentClasses = re.findall(source_file_name + ':.(.*.){', fileContents)

			source_to_ib_outlet_mapping[source_file_name] = set(allIBOutlets)

			# Create a relationship between all of the base and derived classes as this may be needed later on
			if parentClasses:
				subclass_to_parent_mapping[source_file_name] = parentClasses[0].split(',')

	return source_to_ib_outlet_mapping, subclass_to_parent_mapping

def find_ib_outlets_in_parent_class(swift_source_ib_outlet_map, subclass_to_parent_mapping, current_child_view_controller):
	parents_ib_outlets = []
	parent_classes = subclass_to_parent_mapping[current_child_view_controller]

	for potential_parent in parent_classes:
		potential_parent = potential_parent.strip()

		if potential_parent in swift_source_ib_outlet_map:
			parents_ib_outlets += swift_source_ib_outlet_map[potential_parent]
	
	return set(parents_ib_outlets)

def validate_ib_outlet_connections(ib_outlet_map):	
	failures = 0
	for key, value in ib_outlet_map.items():
		logger.info("Processing " + key + "...")

		if key in swift_source_ib_outlet_map:
			outlets_defined_in_parent_class = set(find_ib_outlets_in_parent_class(swift_source_ib_outlet_map, subclass_to_parent_mapping, key))
			outlets_defined_in_code = swift_source_ib_outlet_map[key]
			outlets_from_storyboard = value

			result = set()

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

view_controllers_ib_outlet_map, table_view_cell_to_ib_outlet_map, collection_view_cell_to_ib_outlet_map = load_ib_outlets_from_storyboards()
swift_source_ib_outlet_map, subclass_to_parent_mapping = load_ib_outlets_from_swift_source()

validate_ib_outlet_connections(view_controllers_ib_outlet_map)
validate_ib_outlet_connections(table_view_cell_to_ib_outlet_map)
validate_ib_outlet_connections(collection_view_cell_to_ib_outlet_map)

# Remember this is an issue because there is a discrepancy allowed between parent and child - think about what it is
# 2022-02-21 18:22:32 Aryamans-MacBook-Pro.local __main__[95788] CRITICAL Failure: {'imageView', 'fauxTitleLabel'}
# 2022-02-21 18:22:32 Aryamans-MacBook-Pro.local __main__[95788] INFO Processing RulesOfTheRoadInformationalViewController...

# Need to update the regex to look for a ! at the end of the IBOutlet declaraiton, if it's a ? not my problem to handle

# Table View currently fails if the cell has a collection or table view inside of it

# If your Swift class inherits from an ObjC class (which will be fixed) Mitek -> This will be fixed by adding ObjC Support
# If your Swift class inherits IBOutlets from a VC defined in a framework which we don't have the source control for

# TODOS
# Handle .xib
# Handle IBActions

# Edge Cases
# 2 Swift VCs with the same name, but different file paths - this is because I'm just saving the last part of the filepath for the Swift extension
# 2 VCs declared in the same file because we use the filename only so the other VC would be hidden away

