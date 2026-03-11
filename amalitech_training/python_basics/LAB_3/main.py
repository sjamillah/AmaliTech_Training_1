from .library.library_registry import LibraryRegistry
import json
import os

registry = LibraryRegistry()

def add_resource():
	try:
		print("\nResource Types:")
		print("1. Book")
		print("2. EBook")
		print("3. AudioBook")
		print("4. Borrow")
		kind = input("Choose type: ").strip()

		title = input("Title: ").strip()
		author_name = input("Author name: ").strip()
		file_format = None
		duration = None
		borrower_name = None

		if kind == "2":
			file_format = input("File format (e.g. pdf, epub): ").strip()
		elif kind == "3":
			duration = int(input("Duration in minutes: ").strip())
		elif kind == "4":
			borrower_name = input("Borrower name: ").strip()

		resource = registry.create_resource(
			kind=kind,
			title=title,
			author_name=author_name,
			file_format=file_format,
			duration=duration,
			borrower_name=borrower_name,
		)
		print(f"Resource added: {resource}")
		print(f"Generated Resource ID: {resource.resource_id}")
		print(f"Author ID: {resource.author.author_id}")
	except ValueError as e:
		print(f"Could not add resource: {e}")

def borrow_resource():
	resource_id = int(input("Resource ID to borrow: ").strip())
	registry.borrow_resource(resource_id)

def return_resource():
	resource_id = int(input("Resource ID to return: ").strip())
	registry.return_resource(resource_id)
	print("Resource returned (if it existed).")

def list_resources():
	if not registry.resources:
		print("No resources in the library.")
		return
	registry.list_resources()

def search_resources():
	keyword = input("Enter title keyword: ").strip()
	matches = registry.search_by_title(keyword)

	if not matches:
		print("No matches found.")
		return

	for item in matches:
		print(item)

def show_categories():
	categories = registry.categorize_by_type()
	if not categories:
		print("No resources to categorize.")
		return

	for category, items in categories.items():
		print(f"\n{category}:")
		for item in items:
			print(f"- {item.title}")

def show_report():
	lines = registry.generate_report_lines()
	if not lines:
		print("No report data.")
		return

	print("\nLibrary Report:")
	for line in lines:
		print(line)

def save_data():
	file_name = input("Enter file name (default: lab3_library_data.json): ").strip()
	if not file_name:
		file_name = "lab3_library_data.json"
	saved_count = registry.save_to_json(file_name)
	full_path = os.path.abspath(file_name)
	print(f"Saved {saved_count} resource(s) to {full_path}")

def load_data():
	file_name = input("Enter file name (default: lab3_library_data.json): ").strip()
	if not file_name:
		file_name = "lab3_library_data.json"

	replace_input = input("Replace current data? (yes/no, default: yes): ").strip().lower()
	replace = replace_input != "no"

	try:
		loaded_count = registry.load_from_json(file_name, replace=replace)
		full_path = os.path.abspath(file_name)
		mode = "replaced" if replace else "merged"
		print(f"Loaded {loaded_count} resource(s) from {full_path} ({mode} mode)")
	except FileNotFoundError:
		print("File not found.")
	except json.JSONDecodeError:
		print("Invalid JSON file format.")

def menu():
	while True:
		print("\n=== Library Inventory System ===")
		print("1. Add Resource")
		print("2. Borrow Resource")
		print("3. Return Resource")
		print("4. List Resources")
		print("5. Search by Title")
		print("6. Show Categories")
		print("7. Show Report")
		print("8. Save Data")
		print("9. Load Data")
		print("0. Exit")

		choice = input("Select option: ").strip()

		if choice == "1":
			add_resource()
		elif choice == "2":
			borrow_resource()
		elif choice == "3":
			return_resource()
		elif choice == "4":
			list_resources()
		elif choice == "5":
			search_resources()
		elif choice == "6":
			show_categories()
		elif choice == "7":
			show_report()
		elif choice == "8":
			save_data()
		elif choice == "9":
			load_data()
		elif choice == "0":
			answer = input("Are you sure you want to exit? (Yes/No): ").strip().lower()
			if answer == "yes":
				print("Goodbye")
				break
			print("Returning to menu...")
		else:
			print("Invalid choice. Try again.")


if __name__ == "__main__":
	menu()
