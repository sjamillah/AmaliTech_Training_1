-- ============================================================
-- Online Learning Platform - PostgreSQL Schema
-- ============================================================

-- Drop everything cleanly before recreating
DROP TABLE IF EXISTS lesson_completions    CASCADE;
DROP TABLE IF EXISTS enrollments           CASCADE;
DROP TABLE IF EXISTS lessons               CASCADE;
DROP TABLE IF EXISTS modules               CASCADE;
DROP TABLE IF EXISTS course_prerequisites  CASCADE;
DROP TABLE IF EXISTS courses               CASCADE;
DROP TABLE IF EXISTS instructors           CASCADE;
DROP TABLE IF EXISTS students              CASCADE;

-- -------------------------------------------------------
-- Table 1: instructors
-- Who teaches the courses. Independent table, no FKs.
-- -------------------------------------------------------
CREATE TABLE instructors (
    instructor_id SERIAL       PRIMARY KEY,
    full_name     VARCHAR(200) NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    bio           TEXT,
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);

-- -------------------------------------------------------
-- Table 2: students
-- People learning on the platform. Independent table.
-- -------------------------------------------------------
CREATE TABLE students (
    student_id SERIAL       PRIMARY KEY,
    full_name  VARCHAR(200) NOT NULL,
    email      VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

-- -------------------------------------------------------
-- Table 3: courses
-- Each course belongs to one instructor.
-- total_lessons is a cached count for dashboard performance.
-- -------------------------------------------------------
CREATE TABLE courses (
    course_id     SERIAL       PRIMARY KEY,
    title         VARCHAR(300) NOT NULL,
    description   TEXT,
    instructor_id INT          REFERENCES instructors(instructor_id) ON DELETE SET NULL,
    total_lessons INT          DEFAULT 0,  -- updated by trigger or application code
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);

-- -------------------------------------------------------
-- Table 4: course_prerequisites
-- Self-referential: a course can require another course.
-- E.g. "Python Advanced" requires "Python Basics"
-- -------------------------------------------------------
CREATE TABLE course_prerequisites (
    course_id       INT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    prerequisite_id INT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    PRIMARY KEY (course_id, prerequisite_id)  -- composite PK prevents duplicates
);

-- -------------------------------------------------------
-- Table 5: modules
-- Chapters / sections within a course.
-- A course has many modules, ordered by sequence_order.
-- -------------------------------------------------------
CREATE TABLE modules (
    module_id      SERIAL       PRIMARY KEY,
    course_id      INT          NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    title          VARCHAR(300) NOT NULL,
    sequence_order INT          NOT NULL,  -- 1, 2, 3... controls display order
    UNIQUE (course_id, sequence_order)     -- no two modules with same position in a course
);

-- -------------------------------------------------------
-- Table 6: lessons
-- Individual video/text lessons within a module.
-- quiz_data is a JSONB column: stores questions as flexible JSON.
-- -------------------------------------------------------
CREATE TABLE lessons (
    lesson_id      SERIAL       PRIMARY KEY,
    module_id      INT          NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
    title          VARCHAR(300) NOT NULL,
    sequence_order INT          NOT NULL,  -- order within the module
    content_url    TEXT,                   -- link to video or reading material
    duration_mins  INT          DEFAULT 0, -- estimated time in minutes
    quiz_data      JSONB,                  -- NULL if no quiz; JSON structure if has quiz

    UNIQUE (module_id, sequence_order)     -- no duplicate ordering within a module
);

-- -------------------------------------------------------
-- Table 7: enrollments
-- Junction table: connects students to courses (many-to-many).
-- -------------------------------------------------------
CREATE TABLE enrollments (
    enrollment_id SERIAL      PRIMARY KEY,
    student_id    INT         NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    course_id     INT         NOT NULL REFERENCES courses(course_id)  ON DELETE CASCADE,
    enrolled_at   TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (student_id, course_id)  -- a student can only enroll in a course once
);

-- -------------------------------------------------------
-- Table 8: lesson_completions
-- Records each time a student finishes a lesson.
-- This is the main table for calculating progress.
-- -------------------------------------------------------
CREATE TABLE lesson_completions (
    completion_id SERIAL      PRIMARY KEY,
    student_id    INT         NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    lesson_id     INT         NOT NULL REFERENCES lessons(lesson_id)  ON DELETE CASCADE,
    completed_at  TIMESTAMPTZ DEFAULT NOW(),
    score         NUMERIC(5,2),  -- optional: quiz score if lesson has a quiz

    UNIQUE (student_id, lesson_id)  -- a student can only complete a lesson once
);

-- ============================================================
-- PERFORMANCE INDEXES
-- ============================================================

-- Speed up: "find all courses a student is enrolled in"
CREATE INDEX idx_enrollments_student_id ON enrollments(student_id);

-- Speed up: "find all students in a course"
CREATE INDEX idx_enrollments_course_id ON enrollments(course_id);

-- Speed up: "find all lessons a student has completed"
CREATE INDEX idx_completions_student_id ON lesson_completions(student_id);

-- Speed up: "find which students completed a specific lesson"
CREATE INDEX idx_completions_lesson_id ON lesson_completions(lesson_id);

-- Speed up: "find all lessons in a module"
CREATE INDEX idx_lessons_module_id ON lessons(module_id);

-- Speed up: "find all modules in a course"
CREATE INDEX idx_modules_course_id ON modules(course_id);

-- Speed up: JSONB queries on quiz_data (e.g. filtering by quiz version)
CREATE INDEX idx_lessons_quiz_data ON lessons USING GIN(quiz_data);


-- ============================================================
-- SAMPLE DATA: Seed the database with test records
-- ============================================================

-- Instructors
INSERT INTO instructors (full_name, email, bio) VALUES
    ('Dr. Alice Moyo',   'alice@learnhub.com',  'Data Science expert with 10 years of teaching experience'),
    ('Bob Kariuki',      'bob@learnhub.com',    'Full-stack developer and open source contributor'),
    ('Grace Uwimana',    'grace@learnhub.com',  'Database architect specializing in distributed systems');

-- Students
INSERT INTO students (full_name, email) VALUES
    ('Emmanuel Nkurunziza', 'emmanuel@student.com'),
    ('Claudine Mukamana',   'claudine@student.com'),
    ('Jean-Paul Habimana',  'jeanpaul@student.com');

-- Courses
INSERT INTO courses (title, description, instructor_id, total_lessons) VALUES
    ('Python Basics',       'Introduction to Python programming',       1, 6),
    ('SQL Fundamentals',    'Learn relational databases with PostgreSQL', 3, 4),
    ('Advanced Python',     'Decorators, generators, async, and more',  1, 4),
    ('Web Development 101', 'HTML, CSS, and JavaScript fundamentals',   2, 5);

-- Prerequisite: Advanced Python requires Python Basics
INSERT INTO course_prerequisites (course_id, prerequisite_id) VALUES
    (3, 1);  -- course 3 (Advanced Python) requires course 1 (Python Basics)

-- Modules for Python Basics (course_id = 1)
INSERT INTO modules (course_id, title, sequence_order) VALUES
    (1, 'Getting Started',   1),
    (1, 'Data Structures',   2),
    (2, 'SQL Basics',        1),
    (2, 'Joins and Queries', 2);

-- Lessons for module 1 (Getting Started) -- with quiz on lesson 2
INSERT INTO lessons (module_id, title, sequence_order, duration_mins, quiz_data) VALUES
    (1, 'Installing Python',   1, 10, NULL),
    (1, 'Variables and Types', 2, 20,
        '{
            "version": 1,
            "total_points": 20,
            "questions": [
                {
                    "id": 1,
                    "question": "Which of these is a valid Python variable name?",
                    "options": ["2myvar", "my-var", "my_var", "my var"],
                    "correct_answer": "my_var",
                    "points": 10
                },
                {
                    "id": 2,
                    "question": "What type is the value 3.14 in Python?",
                    "options": ["int", "str", "float", "bool"],
                    "correct_answer": "float",
                    "points": 10
                }
            ]
        }'::JSONB
    ),
    (1, 'Functions',           3, 25, NULL),
    (2, 'Lists and Tuples',    1, 30, NULL),
    (2, 'Dictionaries',        2, 25, NULL),
    (2, 'Sets',                3, 20, NULL),
    (3, 'SELECT Statements',   1, 20, NULL),
    (3, 'WHERE and ORDER BY',  2, 25, NULL),
    (4, 'INNER JOIN',          1, 30, NULL),
    (4, 'LEFT and RIGHT JOIN', 2, 30, NULL);

-- Enrollments
INSERT INTO enrollments (student_id, course_id) VALUES
    (1, 1),  -- Emmanuel enrolled in Python Basics
    (1, 2),  -- Emmanuel enrolled in SQL Fundamentals
    (2, 1),  -- Claudine enrolled in Python Basics
    (3, 1),  -- Jean-Paul enrolled in Python Basics
    (3, 2);  -- Jean-Paul enrolled in SQL Fundamentals

-- Lesson completions (with timestamps spread out to test LAG() query)
INSERT INTO lesson_completions (student_id, lesson_id, completed_at) VALUES
    -- Emmanuel completed all 6 Python Basics lessons
    (1, 1, NOW() - INTERVAL '10 days'),
    (1, 2, NOW() - INTERVAL '9 days'),
    (1, 3, NOW() - INTERVAL '8 days'),
    (1, 4, NOW() - INTERVAL '7 days'),
    (1, 5, NOW() - INTERVAL '5 days'),
    (1, 6, NOW() - INTERVAL '3 days'),
    -- Emmanuel completed 2 SQL lessons
    (1, 7, NOW() - INTERVAL '2 days'),
    (1, 8, NOW() - INTERVAL '1 day'),
    -- Claudine completed 3 Python Basics lessons
    (2, 1, NOW() - INTERVAL '6 days'),
    (2, 2, NOW() - INTERVAL '5 days'),
    (2, 3, NOW() - INTERVAL '4 days');
