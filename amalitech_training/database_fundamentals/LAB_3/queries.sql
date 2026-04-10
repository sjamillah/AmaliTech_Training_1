-- ============================================================
-- Complex Queries for Online Learning Platform
-- ============================================================

-- ============================================================
-- QUERY 1: Completion Percentage for All Enrolled Courses
-- ============================================================
-- For a given student, calculate what % of each course they've
-- completed, along with lesson counts.
-- Uses: GROUP BY, LEFT JOIN, NULLIF to prevent division by zero
-- ============================================================

SELECT
    c.course_id,
    c.title                                             AS course_title,
    c.total_lessons                                     AS total_lessons_in_course,

    -- COUNT only non-NULL completion records (LEFT JOIN gives NULL when not completed)
    COUNT(lc.completion_id)                             AS lessons_completed,

    -- ROUND to 2 decimal places
    -- ::NUMERIC casts the integer to decimal for proper division
    -- NULLIF prevents division by zero if total_lessons is 0
    ROUND(
        COUNT(lc.completion_id)::NUMERIC
        / NULLIF(c.total_lessons, 0) * 100,
        2
    )                                                   AS completion_pct

FROM enrollments e

-- Get course details (title, total_lessons)
JOIN courses c ON e.course_id = c.course_id

-- Get all modules in each enrolled course
LEFT JOIN modules m ON m.course_id = c.course_id

-- Get all lessons in those modules
LEFT JOIN lessons l ON l.module_id = m.module_id

-- Match completed lessons for THIS student only
-- LEFT JOIN: keeps all lessons even if student hasn't completed them
LEFT JOIN lesson_completions lc
    ON lc.lesson_id = l.lesson_id
    AND lc.student_id = e.student_id

-- Filter: only show courses for this specific student
WHERE e.student_id = 1  -- replace with actual student_id

-- Group by course to get one row per enrolled course
GROUP BY c.course_id, c.title, c.total_lessons

ORDER BY completion_pct DESC;


-- ============================================================
-- QUERY 2: Time Between Consecutive Lesson Completions (LAG)
-- ============================================================
-- For each completed lesson, find how long it took since the
-- student's PREVIOUS lesson completion.
-- Uses: LAG() window function, PARTITION BY, ORDER BY
-- ============================================================

SELECT
    lc.student_id,
    s.full_name                                         AS student_name,
    c.title                                             AS course_title,
    m.title                                             AS module_title,
    l.title                                             AS lesson_title,
    lc.completed_at,

    -- LAG() = value from the PREVIOUS row in the window
    -- PARTITION BY lc.student_id: each student has their own window
    -- ORDER BY lc.completed_at: rows are in chronological order
    -- The FIRST row per student will have NULL (no previous completion)
    LAG(lc.completed_at) OVER (
        PARTITION BY lc.student_id
        ORDER BY lc.completed_at
    )                                                   AS previous_completion,

    -- Subtract to get the interval (difference between timestamps)
    -- This shows: "how long between this lesson and the last one?"
    lc.completed_at - LAG(lc.completed_at) OVER (
        PARTITION BY lc.student_id
        ORDER BY lc.completed_at
    )                                                   AS time_since_last_lesson

FROM lesson_completions lc

-- Join to get human-readable names
JOIN students s ON lc.student_id = s.student_id
JOIN lessons l  ON lc.lesson_id = l.lesson_id
JOIN modules m  ON l.module_id = m.module_id
JOIN courses c  ON m.course_id = c.course_id

WHERE lc.student_id = 1  -- replace with actual student_id

ORDER BY lc.completed_at;


-- ============================================================
-- QUERY 3: Full Student Dashboard Query
-- ============================================================
-- Returns everything needed to render a student's dashboard:
-- all enrolled courses with progress, instructor, and last activity.
-- This is the query we'll optimize with EXPLAIN ANALYZE.
-- ============================================================

SELECT
    c.course_id,
    c.title                                             AS course_title,
    i.full_name                                         AS instructor_name,
    e.enrolled_at,
    c.total_lessons,

    -- COUNT DISTINCT because same lesson could appear via multiple modules
    COUNT(DISTINCT lc.lesson_id)                        AS lessons_completed,

    ROUND(
        COUNT(DISTINCT lc.lesson_id)::NUMERIC
        / NULLIF(c.total_lessons, 0) * 100,
        1
    )                                                   AS pct_complete,

    -- Most recent lesson activity (NULL if nothing completed yet)
    MAX(lc.completed_at)                                AS last_activity

FROM enrollments e
JOIN courses c        ON e.course_id = c.course_id
JOIN instructors i    ON c.instructor_id = i.instructor_id
LEFT JOIN modules m   ON m.course_id = c.course_id
LEFT JOIN lessons l   ON l.module_id = m.module_id
LEFT JOIN lesson_completions lc
    ON lc.lesson_id = l.lesson_id
    AND lc.student_id = e.student_id

WHERE e.student_id = 1  -- replace with actual student_id

GROUP BY c.course_id, c.title, i.full_name, e.enrolled_at

-- Sort by most recently active course first
ORDER BY last_activity DESC NULLS LAST;


-- ============================================================
-- QUERY 4: EXPLAIN ANALYZE the Dashboard Query
-- ============================================================
-- Before adding indexes, you'll see "Seq Scan" - reading all rows.
-- After adding indexes from schema.sql, you'll see "Index Scan".
-- ============================================================

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT
    c.course_id,
    c.title,
    COUNT(DISTINCT lc.lesson_id)                        AS lessons_completed,
    ROUND(
        COUNT(DISTINCT lc.lesson_id)::NUMERIC
        / NULLIF(c.total_lessons, 0) * 100,
        1
    )                                                   AS pct_complete
FROM enrollments e
JOIN courses c        ON e.course_id = c.course_id
LEFT JOIN modules m   ON m.course_id = c.course_id
LEFT JOIN lessons l   ON l.module_id = m.module_id
LEFT JOIN lesson_completions lc
    ON lc.lesson_id = l.lesson_id
    AND lc.student_id = e.student_id
WHERE e.student_id = 1
GROUP BY c.course_id, c.title, c.total_lessons;


-- ============================================================
-- QUERY 5: Leaderboard - Top Students by Completion
-- ============================================================
-- Find the top 10 students with the highest average completion
-- percentage across all their enrolled courses.
-- ============================================================

SELECT
    s.student_id,
    s.full_name,
    COUNT(DISTINCT e.course_id)                         AS courses_enrolled,
    ROUND(AVG(
        COUNT(DISTINCT lc.lesson_id)::NUMERIC
        / NULLIF(c.total_lessons, 0) * 100
    ) OVER (PARTITION BY s.student_id), 1)              AS avg_completion_pct

FROM students s
JOIN enrollments e ON s.student_id = e.student_id
JOIN courses c     ON e.course_id = c.course_id
LEFT JOIN modules m ON m.course_id = c.course_id
LEFT JOIN lessons l ON l.module_id = m.module_id
LEFT JOIN lesson_completions lc
    ON lc.lesson_id = l.lesson_id
    AND lc.student_id = s.student_id

GROUP BY s.student_id, s.full_name, c.course_id, c.total_lessons
ORDER BY avg_completion_pct DESC
LIMIT 10;


-- ============================================================
-- QUERY 6: Quiz Performance per Lesson
-- ============================================================
-- Uses JSONB to count how many questions each quiz has,
-- and joins with completions to show student scores.
-- ============================================================

SELECT
    l.lesson_id,
    l.title                                             AS lesson_title,
    c.title                                             AS course_title,
    l.quiz_data ->> 'total_points'                     AS total_possible_points,
    jsonb_array_length(l.quiz_data -> 'questions')      AS num_questions,
    lc.score                                            AS student_score,
    s.full_name                                         AS student_name
FROM lessons l
JOIN modules m ON l.module_id = m.module_id
JOIN courses c ON m.course_id = c.course_id
LEFT JOIN lesson_completions lc ON lc.lesson_id = l.lesson_id
LEFT JOIN students s ON lc.student_id = s.student_id
WHERE l.quiz_data IS NOT NULL  -- only lessons with quizzes
ORDER BY c.title, l.lesson_id;
