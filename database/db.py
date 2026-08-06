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
