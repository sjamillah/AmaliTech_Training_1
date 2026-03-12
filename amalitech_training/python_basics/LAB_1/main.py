from .students.student_registry import StudentRegistry
from .courses.course_registry import CourseRegistry
from .enrollment.enrollment_registry import EnrollmentRegistry

student_registry = StudentRegistry()
course_registry = CourseRegistry()
enroll_manager = EnrollmentRegistry()

def add_student():
    name = input("Student name: ").strip().upper()
    if not name:
        print("Student name is required")
        return

    try:
        age = int(input("Age: "))
        year = int(input("Year: "))
    except ValueError:
        print("Age and Year must be whole numbers")
        return

    student_type = input("Student type (regular/undergraduate/graduate): ").strip().lower()

    if student_type == "undergraduate":
        major = input("Major: ").strip()
        student = student_registry.add_student(name, age, year, student_type="undergraduate", major=major)
    elif student_type == "graduate":
        research_topic = input("Research topic: ").strip()
        student = student_registry.add_student(
            name,
            age,
            year,
            student_type="graduate",
            research_topic=research_topic,
        )
    else:
        student = student_registry.add_student(name, age, year, student_type="regular")

    print(f"Student added: {student}")

def add_course():
    code = input("Course code: ").strip().upper()
    name = input("Course name: ").strip()
    facilitator = input("Facilitator: ").strip()

    if not code or not name or not facilitator:
        print("Course code, name, and facilitator are required")
        return

    course = course_registry.add_course(code, name, facilitator)

    print(f"Course added {course}")

def enroll_student():
    student_id = input("Student ID: ").strip().upper()
    course_code = input("Course code: ").strip().upper()

    if not student_registry.get_student(student_id):
        print("Student ID not found")
        return

    if not course_registry.get_course(course_code):
        print("Course code not found")
        return

    try:
        grade = float(input("Enter grade (0-100): "))
    except ValueError:
        print("Grade must be a number")
        return

    enroll_manager.enroll_student(student_id, course_code)
    enroll_manager.assign_grade(student_id, course_code, grade)

    print("Student enrolled and grade recorded")

def show_students():
    for student in student_registry.get_all_students():
        print(student)

def show_courses():
    for course in course_registry.get_all_courses():
        print(course)

def show_reports():
    for (student_id, course_code), grade in enroll_manager.grades.items():

        student = student_registry.get_student(student_id)
        course = course_registry.get_course(course_code)

        if not student or not course:
            print(f"Skipping invalid report entry: {student_id} | {course_code}")
            continue

        print(f"{student.name} | {course.course_name} | Grade: {grade}")

def show_student_reports():
    students = student_registry.get_all_students()
    if not students:
        print("No students in registry.")
        return

    for student in students:
        print(student.generate_report())

def calculate_average():
    if not enroll_manager.grades:
        print("No grades recorded.")
        return
    
    avg = sum(enroll_manager.grades.values()) / len(enroll_manager.grades)

    print(f"Average grade: {avg:.2f}")

def menu():
    while True:
        print("=== Student Management System ===")
        print("1. Add Student")
        print("2. Add Course")
        print("3. Enroll student")
        print("4. Show students")
        print("5. Show courses")
        print("6. Show reports")
        print("7. Calculate average grade")
        print("8. Show student type reports")
        print("0. Exit")

        choice = input("Select option: ")

        try:
            if choice == '1':
                add_student()

            elif choice == '2':
                add_course()

            elif choice == '3':
                enroll_student()

            elif choice == '4':
                show_students()

            elif choice == '5':
                show_courses()

            elif choice == '6':
                show_reports()

            elif choice == '7':
                calculate_average()

            elif choice == '8':
                show_student_reports()

            elif choice == '0':
                answer = input("Are you sure you want to exit? (Yes/No): ").strip().lower()
                if answer == "yes":
                    print("Goodbye")
                    break
                else:
                    print("Returning to menu....")

            else:
                print("Invalid choice")
        except ValueError as error:
            print(f"Error: {error}")

if __name__ == "__main__":
    menu()
