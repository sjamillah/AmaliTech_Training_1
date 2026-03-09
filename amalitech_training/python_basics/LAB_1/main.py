from .students.student_registry import StudentRegistry
from .courses.course_registry import CourseRegistry
from .enrollment.enrollment_registry import EnrollmentRegistry

student_registry = StudentRegistry()
course_registry = CourseRegistry()
enroll_manager = EnrollmentRegistry()

def add_student():
    name = input("Student name: ").upper()
    age = int(input("Age: "))
    year = int(input("Year: "))
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
    code = input("Course code: ")
    name = input("Course name: ")
    facilitator = input("Facilitator: ")

    course = course_registry.add_course(code, name, facilitator)

    print(f"Course added {course}")

def enroll_student():
    student_id = input("Student ID: ")
    course_code = input("Course code: ")

    grade = float(input("Enter grade (0-100): "))

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

if __name__ == "__main__":
    menu()
