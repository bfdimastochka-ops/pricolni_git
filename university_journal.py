"""
Журнал студентів університету (SQLite).

Реалізує базу даних SQLite з таблицями:
- students (id, name, age, major)
- courses (course_id, course_name, instructor)
- student_courses (student_id, course_id) — зв'язок "багато-до-багатьох"

Підтримує консольний інтерфейс, гнучку фільтрацію та розширені SQL-запити
(JOIN, GROUP BY, агрегатні функції, пошук за шаблоном).
У неінтерактивному середовищі (без вводу з клавіатури) автоматично запускає
демонстраційний режим.
"""

import sqlite3
import sys
from pathlib import Path
from typing import Iterable, Optional

DB_PATH = Path("university.db")


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Повертає підключення до SQLite із зовнішніми ключами та Unicode LOWER."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.create_function("LOWER", 1, lambda s: s.lower() if isinstance(s, str) else s)
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """Створює таблиці students, courses та student_courses, якщо їх ще немає."""
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL CHECK (age > 0),
                major TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS courses (
                course_id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_name TEXT NOT NULL,
                instructor TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS student_courses (
                student_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                PRIMARY KEY (student_id, course_id),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE
            );
            """
        )


# ---------------------------------------------------------------------------
# Базові CRUD-операції
# ---------------------------------------------------------------------------

def add_student(name: str, age: int, major: str, db_path: Path = DB_PATH) -> int:
    """Додає студента і повертає його id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO students (name, age, major) VALUES (?, ?, ?)",
            (name.strip(), age, major.strip()),
        )
        return int(cursor.lastrowid)


def add_course(course_name: str, instructor: str, db_path: Path = DB_PATH) -> int:
    """Додає курс і повертає його course_id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO courses (course_name, instructor) VALUES (?, ?)",
            (course_name.strip(), instructor.strip()),
        )
        return int(cursor.lastrowid)


def enroll_student(student_id: int, course_id: int, db_path: Path = DB_PATH) -> bool:
    """Записує студента на курс. Повертає False, якщо запис уже існує."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO student_courses (student_id, course_id)
            VALUES (?, ?)
            """,
            (student_id, course_id),
        )
        return cursor.rowcount > 0


def update_student(
    student_id: int,
    name: Optional[str] = None,
    age: Optional[int] = None,
    major: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> bool:
    """Оновлює передані поля студента за його id."""
    fields: list[str] = []
    params: list[object] = []
    if name is not None:
        fields.append("name = ?")
        params.append(name.strip())
    if age is not None:
        fields.append("age = ?")
        params.append(age)
    if major is not None:
        fields.append("major = ?")
        params.append(major.strip())

    if not fields:
        return False

    params.append(student_id)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE students SET {', '.join(fields)} WHERE id = ?",
            params,
        )
        return cursor.rowcount > 0


def delete_student(student_id: int, db_path: Path = DB_PATH) -> bool:
    """Видаляє студента за id (пов'язані записи в student_courses видаляються каскадно)."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        return cursor.rowcount > 0


def delete_course(course_id: int, db_path: Path = DB_PATH) -> bool:
    """Видаляє курс за course_id."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM courses WHERE course_id = ?", (course_id,))
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Фільтрація та розширені SQL-запити
# ---------------------------------------------------------------------------

def filter_students(
    name_query: Optional[str] = None,
    major: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    sort_by: str = "id",
    descending: bool = False,
    db_path: Path = DB_PATH,
) -> list[sqlite3.Row]:
    """Фільтрує студентів за ім'ям, спеціальністю, діапазоном віку та сортує результат."""
    allowed_sort = {"id", "name", "age", "major"}
    order_col = sort_by if sort_by in allowed_sort else "id"
    direction = "DESC" if descending else "ASC"

    conditions: list[str] = []
    params: list[object] = []

    if name_query:
        conditions.append("LOWER(name) LIKE LOWER(?)")
        params.append(f"%{name_query.strip()}%")
    if major:
        conditions.append("LOWER(major) LIKE LOWER(?)")
        params.append(f"%{major.strip()}%")
    if min_age is not None:
        conditions.append("age >= ?")
        params.append(min_age)
    if max_age is not None:
        conditions.append("age <= ?")
        params.append(max_age)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT id, name, age, major
        FROM students
        {where_clause}
        ORDER BY {order_col} {direction}
    """
    with get_connection(db_path) as conn:
        return conn.execute(query, params).fetchall()


def filter_courses(
    course_name_query: Optional[str] = None,
    instructor_query: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> list[sqlite3.Row]:
    """Фільтрує курси за назвою або викладачем."""
    conditions: list[str] = []
    params: list[object] = []

    if course_name_query:
        conditions.append("LOWER(course_name) LIKE LOWER(?)")
        params.append(f"%{course_name_query.strip()}%")
    if instructor_query:
        conditions.append("LOWER(instructor) LIKE LOWER(?)")
        params.append(f"%{instructor_query.strip()}%")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT course_id, course_name, instructor
        FROM courses
        {where_clause}
        ORDER BY course_id ASC
    """
    with get_connection(db_path) as conn:
        return conn.execute(query, params).fetchall()


def get_students_by_course(course_id: int, db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    """Розширений запит (INNER JOIN): студенти, записані на конкретний курс."""
    query = """
        SELECT s.id, s.name, s.age, s.major, c.course_name, c.instructor
        FROM students AS s
        INNER JOIN student_courses AS sc ON s.id = sc.student_id
        INNER JOIN courses AS c ON c.course_id = sc.course_id
        WHERE c.course_id = ?
        ORDER BY s.name ASC
    """
    with get_connection(db_path) as conn:
        return conn.execute(query, (course_id,)).fetchall()


def get_courses_by_student(student_id: int, db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    """Розширений запит (INNER JOIN): курси, на які записаний конкретний студент."""
    query = """
        SELECT c.course_id, c.course_name, c.instructor
        FROM courses AS c
        INNER JOIN student_courses AS sc ON c.course_id = sc.course_id
        WHERE sc.student_id = ?
        ORDER BY c.course_name ASC
    """
    with get_connection(db_path) as conn:
        return conn.execute(query, (student_id,)).fetchall()


def get_course_statistics(
    min_students: int = 0,
    db_path: Path = DB_PATH,
) -> list[sqlite3.Row]:
    """Розширений запит (LEFT JOIN + GROUP BY + HAVING): статистика по курсах."""
    query = """
        SELECT
            c.course_id,
            c.course_name,
            c.instructor,
            COUNT(sc.student_id) AS student_count,
            ROUND(AVG(s.age), 1) AS avg_age
        FROM courses AS c
        LEFT JOIN student_courses AS sc ON c.course_id = sc.course_id
        LEFT JOIN students AS s ON s.id = sc.student_id
        GROUP BY c.course_id, c.course_name, c.instructor
        HAVING COUNT(sc.student_id) >= ?
        ORDER BY student_count DESC, c.course_name ASC
    """
    with get_connection(db_path) as conn:
        return conn.execute(query, (min_students,)).fetchall()


def get_major_statistics(db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    """Розширений запит (GROUP BY + агрегатні функції): статистика за спеціальностями."""
    query = """
        SELECT
            major,
            COUNT(*) AS student_count,
            ROUND(AVG(age), 1) AS avg_age,
            MIN(age) AS min_age,
            MAX(age) AS max_age
        FROM students
        GROUP BY major
        ORDER BY student_count DESC, major ASC
    """
    with get_connection(db_path) as conn:
        return conn.execute(query).fetchall()


def get_unenrolled_students(db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    """Розширений запит (LEFT JOIN ... IS NULL): студенти без жодного курсу."""
    query = """
        SELECT s.id, s.name, s.age, s.major
        FROM students AS s
        LEFT JOIN student_courses AS sc ON s.id = sc.student_id
        WHERE sc.course_id IS NULL
        ORDER BY s.id ASC
    """
    with get_connection(db_path) as conn:
        return conn.execute(query).fetchall()


def seed_sample_data(db_path: Path = DB_PATH, quiet: bool = False) -> None:
    """Додає демонстраційні записи, якщо база порожня."""
    with get_connection(db_path) as conn:
        student_count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        course_count = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]

    if student_count > 0 or course_count > 0:
        if not quiet:
            print("База даних уже містить записи. Демонстраційні дані не додано.")
        return

    s1 = add_student("Олександр Коваленко", 20, "Комп'ютерні науки", db_path)
    s2 = add_student("Марія Шевченко", 19, "Прикладна математика", db_path)
    s3 = add_student("Дмитро Бондаренко", 22, "Комп'ютерні науки", db_path)
    s4 = add_student("Ірина Мельник", 21, "Кібербезпека", db_path)
    add_student("Тарас Ткаченко", 18, "Прикладна математика", db_path)

    c1 = add_course("Бази даних", "проф. Іван Петренко", db_path)
    c2 = add_course("Алгоритми та структури даних", "доц. Олена Савченко", db_path)
    c3 = add_course("Криптографія", "доц. Андрій Лисенко", db_path)

    enroll_student(s1, c1, db_path)
    enroll_student(s1, c2, db_path)
    enroll_student(s2, c2, db_path)
    enroll_student(s3, c1, db_path)
    enroll_student(s4, c1, db_path)
    enroll_student(s4, c3, db_path)
    if not quiet:
        print("Демонстраційні дані успішно додано.")


# ---------------------------------------------------------------------------
# Консольний інтерфейс (CLI) та демонстраційний режим
# ---------------------------------------------------------------------------

def print_table(headers: list[str], rows: Iterable[sqlite3.Row]) -> None:
    """Форматований вивід таблиці в консоль."""
    data = [[("-" if val is None else str(val)) for val in row] for row in rows]
    if not data:
        print("  (Немає записів за вашим запитом)")
        return

    widths = [
        max(len(headers[i]), max(len(r[i]) for r in data))
        for i in range(len(headers))
    ]
    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    header_line = "| " + " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))) + " |"

    print(sep)
    print(header_line)
    print(sep)
    for row in data:
        print("| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    print(sep)


def run_demo(db_path: Path = DB_PATH) -> None:
    """Демонстраційний запуск для середовищ без інтерактивного вводу (stdin)."""
    init_db(db_path)
    seed_sample_data(db_path, quiet=True)

    print("\n[Неінтерактивне середовище: запущено демонстрацію роботи БД]\n")

    print("1. Усі студенти (таблиця students):")
    print_table(["ID", "Ім'я", "Вік", "Спеціальність"], filter_students(db_path=db_path))

    print("\n2. Усі курси (таблиця courses):")
    print_table(["ID курсу", "Назва курсу", "Викладач"], filter_courses(db_path=db_path))

    print("\n3. Фільтрація студентів (спеціальність містить 'комп', вік >= 20, спадання за віком):")
    print_table(
        ["ID", "Ім'я", "Вік", "Спеціальність"],
        filter_students(major="комп", min_age=20, sort_by="age", descending=True, db_path=db_path),
    )

    print("\n4. Розширений запит (INNER JOIN) — студенти курсу 'Бази даних' (course_id = 1):")
    print_table(
        ["ID", "Ім'я", "Вік", "Спеціальність", "Курс", "Викладач"],
        get_students_by_course(1, db_path),
    )

    print("\n5. Розширений запит (LEFT JOIN + GROUP BY) — статистика по курсах:")
    print_table(
        ["ID курсу", "Назва курсу", "Викладач", "Студентів", "Середній вік"],
        get_course_statistics(db_path=db_path),
    )

    print("\n6. Розширений запит (GROUP BY + агрегати) — статистика за спеціальностями:")
    print_table(
        ["Спеціальність", "Студентів", "Сер. вік", "Мін. вік", "Макс. вік"],
        get_major_statistics(db_path),
    )

    print("\n7. Розширений запит (LEFT JOIN ... IS NULL) — студенти без курсів:")
    print_table(["ID", "Ім'я", "Вік", "Спеціальність"], get_unenrolled_students(db_path))


def prompt_non_empty(label: str) -> str:
    while True:
        value = input(label).strip()
        if value:
            return value
        print("Поле не може бути порожнім. Спробуйте ще раз.")


def prompt_int(label: str, min_value: Optional[int] = None, allow_empty: bool = False) -> Optional[int]:
    while True:
        raw = input(label).strip()
        if allow_empty and raw == "":
            return None
        try:
            value = int(raw)
            if min_value is not None and value < min_value:
                print(f"Введіть ціле число не менше {min_value}.")
                continue
            return value
        except ValueError:
            print("Помилка: введіть коректне ціле число.")


def menu_advanced_queries(db_path: Path = DB_PATH) -> None:
    """Підменю розширених SQL-запитів."""
    print("\n--- Розширені SQL-запити ---")
    print("1. Студенти конкретного курсу (INNER JOIN)")
    print("2. Курси конкретного студента (INNER JOIN)")
    print("3. Статистика по курсах: кількість студентів і середній вік (LEFT JOIN + GROUP BY)")
    print("4. Статистика за спеціальностями (GROUP BY + AVG/MIN/MAX)")
    print("5. Студенти, які не записані на жоден курс (LEFT JOIN ... IS NULL)")

    sub = input("Оберіть запит (1-5): ").strip()
    if sub == "1":
        course_id = prompt_int("Введіть ID курсу: ", min_value=1)
        rows = get_students_by_course(course_id, db_path)
        print_table(["ID", "Ім'я", "Вік", "Спеціальність", "Курс", "Викладач"], rows)
    elif sub == "2":
        student_id = prompt_int("Введіть ID студента: ", min_value=1)
        rows = get_courses_by_student(student_id, db_path)
        print_table(["ID курсу", "Назва курсу", "Викладач"], rows)
    elif sub == "3":
        min_st = prompt_int("Мін. кількість студентів (Enter = 0): ", min_value=0, allow_empty=True)
        rows = get_course_statistics(min_st or 0, db_path)
        print_table(["ID курсу", "Назва курсу", "Викладач", "Студентів", "Середній вік"], rows)
    elif sub == "4":
        rows = get_major_statistics(db_path)
        print_table(["Спеціальність", "Студентів", "Сер. вік", "Мін. вік", "Макс. вік"], rows)
    elif sub == "5":
        rows = get_unenrolled_students(db_path)
        print_table(["ID", "Ім'я", "Вік", "Спеціальність"], rows)
    else:
        print("Невірний вибір.")


def run_cli(db_path: Path = DB_PATH) -> None:
    """Головний цикл консольного інтерфейсу з коректною обробкою EOF."""
    init_db(db_path)
    actions_taken = 0

    try:
        while True:
            print("\n=== Журнал студентів університету ===")
            print("1. Додати студента")
            print("2. Додати курс")
            print("3. Записати студента на курс")
            print("4. Показати всіх студентів")
            print("5. Показати всі курси")
            print("6. Фільтрація та сортування студентів")
            print("7. Фільтрація курсів")
            print("8. Розширені SQL-запити та статистика")
            print("9. Оновити або видалити запис")
            print("10. Заповнити базу тестовими даними")
            print("0. Вихід")

            choice = input("Оберіть дію: ").strip()
            actions_taken += 1

            if choice == "1":
                name = prompt_non_empty("ПІБ студента: ")
                age = prompt_int("Вік студента: ", min_value=1)
                major = prompt_non_empty("Спеціальність: ")
                new_id = add_student(name, age, major, db_path)
                print(f"Студента додано з ID = {new_id}.")

            elif choice == "2":
                course_name = prompt_non_empty("Назва курсу: ")
                instructor = prompt_non_empty("Викладач: ")
                new_id = add_course(course_name, instructor, db_path)
                print(f"Курс додано з course_id = {new_id}.")

            elif choice == "3":
                student_id = prompt_int("ID студента: ", min_value=1)
                course_id = prompt_int("ID курсу: ", min_value=1)
                try:
                    if enroll_student(student_id, course_id, db_path):
                        print("Студента успішно записано на курс.")
                    else:
                        print("Студент уже записаний на цей курс.")
                except sqlite3.IntegrityError:
                    print("Помилка: вказаний ID студента або курсу не існує.")

            elif choice == "4":
                print_table(["ID", "Ім'я", "Вік", "Спеціальність"], filter_students(db_path=db_path))

            elif choice == "5":
                print_table(["ID курсу", "Назва курсу", "Викладач"], filter_courses(db_path=db_path))

            elif choice == "6":
                print("\n--- Фільтрація студентів (залиште порожнім, щоб пропустити) ---")
                name_q = input("Пошук за ім'ям: ").strip() or None
                major_q = input("Спеціальність: ").strip() or None
                min_age = prompt_int("Мінімальний вік: ", min_value=1, allow_empty=True)
                max_age = prompt_int("Максимальний вік: ", min_value=1, allow_empty=True)
                sort_by = input("Сортувати за (id/name/age/major) [id]: ").strip() or "id"
                desc = input("У зворотному порядку? (y/n) [n]: ").strip().lower() == "y"
                rows = filter_students(name_q, major_q, min_age, max_age, sort_by, desc, db_path)
                print_table(["ID", "Ім'я", "Вік", "Спеціальність"], rows)

            elif choice == "7":
                print("\n--- Фільтрація курсів (залиште порожнім, щоб пропустити) ---")
                c_name = input("Назва курсу: ").strip() or None
                instr = input("Викладач: ").strip() or None
                rows = filter_courses(c_name, instr, db_path)
                print_table(["ID курсу", "Назва курсу", "Викладач"], rows)

            elif choice == "8":
                menu_advanced_queries(db_path)

            elif choice == "9":
                print("1. Оновити студента | 2. Видалити студента | 3. Видалити курс")
                act = input("Оберіть дію (1-3): ").strip()
                if act == "1":
                    sid = prompt_int("ID студента: ", min_value=1)
                    new_name = input("Нове ім'я (Enter = без змін): ").strip() or None
                    new_age = prompt_int("Новий вік (Enter = без змін): ", min_value=1, allow_empty=True)
                    new_major = input("Нова спеціальність (Enter = без змін): ").strip() or None
                    if update_student(sid, new_name, new_age, new_major, db_path):
                        print("Дані студента оновлено.")
                    else:
                        print("Студента не знайдено або змін не задано.")
                elif act == "2":
                    sid = prompt_int("ID студента для видалення: ", min_value=1)
                    print("Студента видалено." if delete_student(sid, db_path) else "Студента не знайдено.")
                elif act == "3":
                    cid = prompt_int("ID курсу для видалення: ", min_value=1)
                    print("Курс видалено." if delete_course(cid, db_path) else "Курс не знайдено.")

            elif choice == "10":
                seed_sample_data(db_path)

            elif choice == "0":
                print("Роботу завершено.")
                break
            else:
                print("Невірна команда. Оберіть пункт із меню.")
    except EOFError:
        if actions_taken == 0:
            run_demo(db_path)
        else:
            print("\nПотік вводу завершено. Роботу програми зупинено.")
    except KeyboardInterrupt:
        print("\nРоботу завершено користувачем.")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        run_demo()
    else:
        run_cli()