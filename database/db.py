import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


DB_PATH = Path(__file__).resolve().parent.parent / "clinic_income.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as database:
        await database.execute("PRAGMA foreign_keys = ON")

        await database.execute(
            """
            CREATE TABLE IF NOT EXISTS clinics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                primary_price INTEGER NOT NULL CHECK(primary_price > 0),
                secondary_price INTEGER NOT NULL CHECK(secondary_price > 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK(is_active IN (0, 1))
            )
            """
        )

        columns_cursor = await database.execute(
            "PRAGMA table_info(clinics)"
        )
        clinic_columns = {
            str(row[1])
            for row in await columns_cursor.fetchall()
        }

        if "is_active" not in clinic_columns:
            await database.execute(
                """
                ALTER TABLE clinics
                ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1
                    CHECK(is_active IN (0, 1))
                """
            )

        await database.execute(
            """
            CREATE TABLE IF NOT EXISTS specialties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clinic_id INTEGER NOT NULL,
                name TEXT NOT NULL COLLATE NOCASE,
                primary_price INTEGER NOT NULL CHECK(primary_price > 0),
                secondary_price INTEGER NOT NULL CHECK(secondary_price > 0),
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK(is_active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (clinic_id)
                    REFERENCES clinics(id)
                    ON DELETE RESTRICT
            )
            """
        )

        await database.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
                idx_specialties_active_name
            ON specialties(clinic_id, name COLLATE NOCASE)
            WHERE is_active = 1
            """
        )

        await database.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_specialties_clinic
            ON specialties(clinic_id, is_active)
            """
        )

        await database.execute(
            """
            CREATE TABLE IF NOT EXISTS income_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adjustment_date TEXT NOT NULL,
                primary_count INTEGER NOT NULL
                    CHECK(primary_count >= 0),
                secondary_count INTEGER NOT NULL
                    CHECK(secondary_count >= 0),
                amount INTEGER NOT NULL CHECK(amount >= 0),
                note TEXT NOT NULL DEFAULT '',
                source_key TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        await database.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_income_adjustments_date
            ON income_adjustments(adjustment_date)
            """
        )

        await database.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_date TEXT NOT NULL,
                clinic_id INTEGER NOT NULL,
                specialty_id INTEGER NOT NULL,
                primary_count INTEGER NOT NULL
                    CHECK(primary_count >= 0),
                secondary_count INTEGER NOT NULL
                    CHECK(secondary_count >= 0),
                primary_amount INTEGER NOT NULL
                    CHECK(primary_amount >= 0),
                secondary_amount INTEGER NOT NULL
                    CHECK(secondary_amount >= 0),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(work_date, clinic_id, specialty_id),
                FOREIGN KEY (clinic_id)
                    REFERENCES clinics(id)
                    ON DELETE RESTRICT,
                FOREIGN KEY (specialty_id)
                    REFERENCES specialties(id)
                    ON DELETE RESTRICT
            )
            """
        )

        await database.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_daily_entries_date
            ON daily_entries(work_date)
            """
        )

        await database.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clinic_id INTEGER NOT NULL,
                specialty_id INTEGER,
                visit_type TEXT NOT NULL
                    CHECK(visit_type IN ('primary', 'secondary')),
                amount INTEGER NOT NULL CHECK(amount > 0),
                created_at TEXT NOT NULL,
                FOREIGN KEY (clinic_id)
                    REFERENCES clinics(id)
                    ON DELETE RESTRICT
            )
            """
        )

        appointment_columns_cursor = await database.execute(
            "PRAGMA table_info(appointments)"
        )
        appointment_columns = {
            str(row[1])
            for row in await appointment_columns_cursor.fetchall()
        }

        if "specialty_id" not in appointment_columns:
            await database.execute(
                """
                ALTER TABLE appointments
                ADD COLUMN specialty_id INTEGER
                    REFERENCES specialties(id)
                """
            )

        await database.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_appointments_specialty
            ON appointments(specialty_id)
            """
        )

        await database.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_appointments_created_at
            ON appointments(created_at)
            """
        )

        await database.commit()


async def add_clinic(
    name: str,
    primary_price: int,
    secondary_price: int,
) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as database:
            await database.execute(
                """
                INSERT INTO clinics (
                    name,
                    primary_price,
                    secondary_price,
                    is_active
                )
                VALUES (?, ?, ?, 1)
                """,
                (
                    name,
                    primary_price,
                    secondary_price,
                ),
            )
            await database.commit()

        return True

    except sqlite3.IntegrityError:
        return False


async def get_clinics() -> list[tuple[int, str, int, int]]:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            SELECT
                id,
                name,
                primary_price,
                secondary_price
            FROM clinics
            WHERE is_active = 1
            ORDER BY name
            """
        )

        rows = await cursor.fetchall()

    return rows


async def get_clinic_by_id(
    clinic_id: int,
) -> tuple[int, str, int, int] | None:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            SELECT
                id,
                name,
                primary_price,
                secondary_price
            FROM clinics
            WHERE id = ?
              AND is_active = 1
            """,
            (clinic_id,),
        )

        row = await cursor.fetchone()

    return row


async def update_clinic(
    clinic_id: int,
    name: str,
    primary_price: int,
    secondary_price: int,
) -> str:
    try:
        async with aiosqlite.connect(DB_PATH) as database:
            cursor = await database.execute(
                """
                UPDATE clinics
                SET
                    name = ?,
                    primary_price = ?,
                    secondary_price = ?
                WHERE id = ?
                  AND is_active = 1
                """,
                (
                    name,
                    primary_price,
                    secondary_price,
                    clinic_id,
                ),
            )
            await database.commit()

            if cursor.rowcount == 0:
                return "not_found"

        return "updated"

    except sqlite3.IntegrityError:
        return "duplicate_name"


async def update_clinic_prices(
    clinic_id: int,
    primary_price: int,
    secondary_price: int,
) -> bool:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            UPDATE clinics
            SET
                primary_price = ?,
                secondary_price = ?
            WHERE id = ?
              AND is_active = 1
            """,
            (
                primary_price,
                secondary_price,
                clinic_id,
            ),
        )
        await database.commit()

        updated = cursor.rowcount > 0

    return updated


async def archive_clinic(clinic_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as database:
        await database.execute("PRAGMA foreign_keys = ON")
        await database.execute("BEGIN")

        cursor = await database.execute(
            """
            UPDATE clinics
            SET is_active = 0
            WHERE id = ?
              AND is_active = 1
            """,
            (clinic_id,),
        )

        if cursor.rowcount == 0:
            await database.rollback()
            return False

        await database.execute(
            """
            UPDATE specialties
            SET is_active = 0
            WHERE clinic_id = ?
              AND is_active = 1
            """,
            (clinic_id,),
        )

        await database.commit()

    return True


async def add_specialty(
    clinic_id: int,
    name: str,
    primary_price: int,
    secondary_price: int,
) -> str:
    clinic = await get_clinic_by_id(clinic_id)

    if clinic is None:
        return "clinic_not_found"

    try:
        async with aiosqlite.connect(DB_PATH) as database:
            await database.execute(
                """
                INSERT INTO specialties (
                    clinic_id,
                    name,
                    primary_price,
                    secondary_price,
                    is_active
                )
                VALUES (?, ?, ?, ?, 1)
                """,
                (
                    clinic_id,
                    name,
                    primary_price,
                    secondary_price,
                ),
            )
            await database.commit()

        return "created"

    except sqlite3.IntegrityError:
        return "duplicate_name"


async def get_specialties(
    clinic_id: int,
) -> list[tuple[int, str, int, int]]:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            SELECT
                id,
                name,
                primary_price,
                secondary_price
            FROM specialties
            WHERE clinic_id = ?
              AND is_active = 1
            ORDER BY name
            """,
            (clinic_id,),
        )

        rows = await cursor.fetchall()

    return rows


async def get_specialty_by_id(
    specialty_id: int,
) -> tuple[int, int, str, int, int] | None:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            SELECT
                specialties.id,
                specialties.clinic_id,
                specialties.name,
                specialties.primary_price,
                specialties.secondary_price
            FROM specialties
            INNER JOIN clinics
                ON clinics.id = specialties.clinic_id
            WHERE specialties.id = ?
              AND specialties.is_active = 1
              AND clinics.is_active = 1
            """,
            (specialty_id,),
        )

        row = await cursor.fetchone()

    return row


async def update_specialty(
    specialty_id: int,
    name: str,
    primary_price: int,
    secondary_price: int,
) -> str:
    try:
        async with aiosqlite.connect(DB_PATH) as database:
            cursor = await database.execute(
                """
                UPDATE specialties
                SET
                    name = ?,
                    primary_price = ?,
                    secondary_price = ?
                WHERE id = ?
                  AND is_active = 1
                """,
                (
                    name,
                    primary_price,
                    secondary_price,
                    specialty_id,
                ),
            )
            await database.commit()

            if cursor.rowcount == 0:
                return "not_found"

        return "updated"

    except sqlite3.IntegrityError:
        return "duplicate_name"


async def archive_specialty(specialty_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            UPDATE specialties
            SET is_active = 0
            WHERE id = ?
              AND is_active = 1
            """,
            (specialty_id,),
        )
        await database.commit()

        archived = cursor.rowcount > 0

    return archived


async def add_clinic_with_specialty(
    clinic_name: str,
    specialty_name: str,
    primary_price: int,
    secondary_price: int,
) -> str:
    async with aiosqlite.connect(DB_PATH) as database:
        await database.execute("PRAGMA foreign_keys = ON")

        try:
            await database.execute("BEGIN")

            cursor = await database.execute(
                """
                SELECT
                    id,
                    is_active
                FROM clinics
                WHERE name = ? COLLATE NOCASE
                LIMIT 1
                """,
                (clinic_name,),
            )
            existing_clinic = await cursor.fetchone()

            if existing_clinic is not None:
                clinic_id = int(existing_clinic[0])
                is_active = bool(existing_clinic[1])

                if is_active:
                    await database.rollback()
                    return "duplicate_clinic"

                await database.execute(
                    """
                    UPDATE clinics
                    SET
                        primary_price = ?,
                        secondary_price = ?,
                        is_active = 1
                    WHERE id = ?
                    """,
                    (
                        primary_price,
                        secondary_price,
                        clinic_id,
                    ),
                )

                await database.execute(
                    """
                    UPDATE specialties
                    SET is_active = 0
                    WHERE clinic_id = ?
                      AND is_active = 1
                    """,
                    (clinic_id,),
                )
            else:
                clinic_cursor = await database.execute(
                    """
                    INSERT INTO clinics (
                        name,
                        primary_price,
                        secondary_price,
                        is_active
                    )
                    VALUES (?, ?, ?, 1)
                    """,
                    (
                        clinic_name,
                        primary_price,
                        secondary_price,
                    ),
                )
                clinic_id = int(clinic_cursor.lastrowid)

            await database.execute(
                """
                INSERT INTO specialties (
                    clinic_id,
                    name,
                    primary_price,
                    secondary_price,
                    is_active
                )
                VALUES (?, ?, ?, ?, 1)
                """,
                (
                    clinic_id,
                    specialty_name,
                    primary_price,
                    secondary_price,
                ),
            )

            await database.commit()

        except sqlite3.IntegrityError:
            await database.rollback()
            return "duplicate_clinic"

    return "created"


async def rename_clinic(
    clinic_id: int,
    new_name: str,
) -> str:
    try:
        async with aiosqlite.connect(DB_PATH) as database:
            cursor = await database.execute(
                """
                UPDATE clinics
                SET name = ?
                WHERE id = ?
                  AND is_active = 1
                """,
                (
                    new_name,
                    clinic_id,
                ),
            )
            await database.commit()

            if cursor.rowcount == 0:
                return "not_found"

        return "updated"

    except sqlite3.IntegrityError:
        return "duplicate_name"


async def get_daily_entry_by_key(
    work_date: str,
    specialty_id: int,
) -> tuple[int, int, int, int, int] | None:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            SELECT
                id,
                primary_count,
                secondary_count,
                primary_amount,
                secondary_amount
            FROM daily_entries
            WHERE work_date = ?
              AND specialty_id = ?
            """,
            (work_date, specialty_id),
        )
        row = await cursor.fetchone()

    return row


async def save_daily_entry(
    work_date: str,
    specialty_id: int,
    primary_count: int,
    secondary_count: int,
) -> tuple[str, str, str, int, int, int, int] | None:
    if primary_count < 0 or secondary_count < 0:
        return None

    if primary_count == 0 and secondary_count == 0:
        return None

    async with aiosqlite.connect(DB_PATH) as database:
        await database.execute("PRAGMA foreign_keys = ON")

        cursor = await database.execute(
            """
            SELECT
                clinics.id,
                clinics.name,
                specialties.name,
                specialties.primary_price,
                specialties.secondary_price
            FROM specialties
            INNER JOIN clinics
                ON clinics.id = specialties.clinic_id
            WHERE specialties.id = ?
              AND specialties.is_active = 1
              AND clinics.is_active = 1
            """,
            (specialty_id,),
        )
        row = await cursor.fetchone()

        if row is None:
            return None

        clinic_id = int(row[0])
        clinic_name = str(row[1])
        specialty_name = str(row[2])
        primary_price = int(row[3])
        secondary_price = int(row[4])
        primary_amount = primary_count * primary_price
        secondary_amount = secondary_count * secondary_price
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        existing_cursor = await database.execute(
            """
            SELECT id
            FROM daily_entries
            WHERE work_date = ?
              AND clinic_id = ?
              AND specialty_id = ?
            """,
            (work_date, clinic_id, specialty_id),
        )
        existing = await existing_cursor.fetchone()
        status = "updated" if existing is not None else "created"

        await database.execute(
            """
            INSERT INTO daily_entries (
                work_date,
                clinic_id,
                specialty_id,
                primary_count,
                secondary_count,
                primary_amount,
                secondary_amount,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(work_date, clinic_id, specialty_id)
            DO UPDATE SET
                primary_count = excluded.primary_count,
                secondary_count = excluded.secondary_count,
                primary_amount = excluded.primary_amount,
                secondary_amount = excluded.secondary_amount,
                updated_at = excluded.updated_at
            """,
            (
                work_date,
                clinic_id,
                specialty_id,
                primary_count,
                secondary_count,
                primary_amount,
                secondary_amount,
                now,
                now,
            ),
        )
        await database.commit()

    return (
        status,
        clinic_name,
        specialty_name,
        primary_count,
        secondary_count,
        primary_amount,
        secondary_amount,
    )


async def get_daily_entry_statistics(
    start_date: str,
    end_date: str,
) -> list[tuple[int, str, int, str, str, int, int]]:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            SELECT
                clinics.id,
                clinics.name,
                specialties.id,
                specialties.name,
                'primary' AS visit_type,
                SUM(daily_entries.primary_count),
                SUM(daily_entries.primary_amount)
            FROM daily_entries
            INNER JOIN clinics
                ON clinics.id = daily_entries.clinic_id
            INNER JOIN specialties
                ON specialties.id = daily_entries.specialty_id
            WHERE daily_entries.work_date >= ?
              AND daily_entries.work_date < ?
              AND daily_entries.primary_count > 0
            GROUP BY
                clinics.id,
                clinics.name,
                specialties.id,
                specialties.name

            UNION ALL

            SELECT
                clinics.id,
                clinics.name,
                specialties.id,
                specialties.name,
                'secondary' AS visit_type,
                SUM(daily_entries.secondary_count),
                SUM(daily_entries.secondary_amount)
            FROM daily_entries
            INNER JOIN clinics
                ON clinics.id = daily_entries.clinic_id
            INNER JOIN specialties
                ON specialties.id = daily_entries.specialty_id
            WHERE daily_entries.work_date >= ?
              AND daily_entries.work_date < ?
              AND daily_entries.secondary_count > 0
            GROUP BY
                clinics.id,
                clinics.name,
                specialties.id,
                specialties.name

            ORDER BY 2, 4, 5
            """,
            (start_date, end_date, start_date, end_date),
        )
        rows = await cursor.fetchall()

    return rows


async def get_last_daily_entry(
) -> tuple[int, str, str, str, int, int, int, int, str] | None:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            SELECT
                daily_entries.id,
                clinics.name,
                specialties.name,
                daily_entries.work_date,
                daily_entries.primary_count,
                daily_entries.secondary_count,
                daily_entries.primary_amount,
                daily_entries.secondary_amount,
                daily_entries.updated_at
            FROM daily_entries
            INNER JOIN clinics
                ON clinics.id = daily_entries.clinic_id
            INNER JOIN specialties
                ON specialties.id = daily_entries.specialty_id
            ORDER BY daily_entries.updated_at DESC, daily_entries.id DESC
            LIMIT 1
            """
        )
        row = await cursor.fetchone()

    return row


async def delete_daily_entry(entry_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            DELETE FROM daily_entries
            WHERE id = ?
            """,
            (entry_id,),
        )
        await database.commit()
        deleted = cursor.rowcount > 0

    return deleted


async def add_specialty_appointment(
    specialty_id: int,
    visit_type: str,
    created_at: str | None = None,
) -> tuple[str, str, int] | None:
    if visit_type not in {"primary", "secondary"}:
        return None

    price_column = (
        "primary_price"
        if visit_type == "primary"
        else "secondary_price"
    )

    async with aiosqlite.connect(DB_PATH) as database:
        await database.execute("PRAGMA foreign_keys = ON")

        cursor = await database.execute(
            f"""
            SELECT
                clinics.id,
                clinics.name,
                specialties.name,
                specialties.{price_column}
            FROM specialties
            INNER JOIN clinics
                ON clinics.id = specialties.clinic_id
            WHERE specialties.id = ?
              AND specialties.is_active = 1
              AND clinics.is_active = 1
            """,
            (specialty_id,),
        )

        row = await cursor.fetchone()

        if row is None:
            return None

        clinic_id = int(row[0])
        clinic_name = str(row[1])
        specialty_name = str(row[2])
        amount = int(row[3])
        appointment_created_at = (
            created_at
            if created_at is not None
            else datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            )
        )

        await database.execute(
            """
            INSERT INTO appointments (
                clinic_id,
                specialty_id,
                visit_type,
                amount,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                clinic_id,
                specialty_id,
                visit_type,
                amount,
                appointment_created_at,
            ),
        )

        await database.commit()

    return clinic_name, specialty_name, amount


async def add_appointment(
    clinic_id: int,
    visit_type: str,
    created_at: str | None = None,
) -> tuple[str, int] | None:
    if visit_type not in {"primary", "secondary"}:
        return None

    price_column = (
        "primary_price"
        if visit_type == "primary"
        else "secondary_price"
    )

    async with aiosqlite.connect(DB_PATH) as database:
        await database.execute("PRAGMA foreign_keys = ON")

        cursor = await database.execute(
            f"""
            SELECT
                name,
                {price_column}
            FROM clinics
            WHERE id = ?
              AND is_active = 1
            """,
            (clinic_id,),
        )

        clinic = await cursor.fetchone()

        if clinic is None:
            return None

        clinic_name = str(clinic[0])
        amount = int(clinic[1])
        appointment_created_at = (
            created_at
            if created_at is not None
            else datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            )
        )

        await database.execute(
            """
            INSERT INTO appointments (
                clinic_id,
                visit_type,
                amount,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                clinic_id,
                visit_type,
                amount,
                appointment_created_at,
            ),
        )

        await database.commit()

    return clinic_name, amount


async def upsert_income_adjustment(
    adjustment_date: str,
    primary_count: int,
    secondary_count: int,
    amount: int,
    note: str,
    source_key: str,
) -> None:
    async with aiosqlite.connect(DB_PATH) as database:
        await database.execute(
            """
            INSERT INTO income_adjustments (
                adjustment_date,
                primary_count,
                secondary_count,
                amount,
                note,
                source_key
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_key) DO UPDATE SET
                adjustment_date = excluded.adjustment_date,
                primary_count = excluded.primary_count,
                secondary_count = excluded.secondary_count,
                amount = excluded.amount,
                note = excluded.note
            """,
            (
                adjustment_date,
                primary_count,
                secondary_count,
                amount,
                note,
                source_key,
            ),
        )
        await database.commit()


async def get_income_adjustment_statistics(
    start_date: str,
    end_date: str,
) -> tuple[int, int, int, str | None, str | None]:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            SELECT
                COALESCE(SUM(primary_count), 0),
                COALESCE(SUM(secondary_count), 0),
                COALESCE(SUM(amount), 0),
                MIN(adjustment_date),
                MAX(adjustment_date)
            FROM income_adjustments
            WHERE adjustment_date >= ?
              AND adjustment_date < ?
            """,
            (
                start_date,
                end_date,
            ),
        )

        row = await cursor.fetchone()

    if row is None:
        return 0, 0, 0, None, None

    return (
        int(row[0]),
        int(row[1]),
        int(row[2]),
        str(row[3]) if row[3] is not None else None,
        str(row[4]) if row[4] is not None else None,
    )


async def get_appointment_statistics(
    start_at: str,
    end_at: str,
) -> list[
    tuple[int, str, int | None, str, str, int, int]
]:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            SELECT
                clinics.id,
                clinics.name,
                specialties.id,
                COALESCE(
                    specialties.name,
                    'Без специальности'
                ) AS specialty_name,
                appointments.visit_type,
                COUNT(appointments.id) AS appointment_count,
                SUM(appointments.amount) AS total_amount
            FROM appointments
            INNER JOIN clinics
                ON clinics.id = appointments.clinic_id
            LEFT JOIN specialties
                ON specialties.id = appointments.specialty_id
            WHERE appointments.created_at >= ?
              AND appointments.created_at < ?
            GROUP BY
                clinics.id,
                clinics.name,
                specialties.id,
                specialties.name,
                appointments.visit_type
            ORDER BY
                clinics.name,
                specialty_name,
                appointments.visit_type
            """,
            (
                start_at,
                end_at,
            ),
        )

        rows = await cursor.fetchall()

    return rows


async def get_last_appointment(
) -> tuple[int, str, str, str, int, str] | None:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            SELECT
                appointments.id,
                clinics.name,
                COALESCE(
                    specialties.name,
                    'Без специальности'
                ) AS specialty_name,
                appointments.visit_type,
                appointments.amount,
                appointments.created_at
            FROM appointments
            INNER JOIN clinics
                ON clinics.id = appointments.clinic_id
            LEFT JOIN specialties
                ON specialties.id = appointments.specialty_id
            ORDER BY
                appointments.created_at DESC,
                appointments.id DESC
            LIMIT 1
            """
        )

        row = await cursor.fetchone()

    return row


async def delete_appointment(appointment_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            DELETE FROM appointments
            WHERE id = ?
            """,
            (appointment_id,),
        )
        await database.commit()

        deleted = cursor.rowcount > 0

    return deleted
