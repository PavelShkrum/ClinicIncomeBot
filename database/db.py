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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        await database.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clinic_id INTEGER NOT NULL,
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
                    secondary_price
                )
                VALUES (?, ?, ?)
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
            """,
            (clinic_id,),
        )

        row = await cursor.fetchone()

    return row


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
) -> list[tuple[int, str, str, int, int]]:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            SELECT
                clinics.id,
                clinics.name,
                appointments.visit_type,
                COUNT(appointments.id) AS appointment_count,
                SUM(appointments.amount) AS total_amount
            FROM appointments
            INNER JOIN clinics
                ON clinics.id = appointments.clinic_id
            WHERE appointments.created_at >= ?
              AND appointments.created_at < ?
            GROUP BY
                clinics.id,
                clinics.name,
                appointments.visit_type
            ORDER BY
                clinics.name,
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
) -> tuple[int, str, str, int, str] | None:
    async with aiosqlite.connect(DB_PATH) as database:
        cursor = await database.execute(
            """
            SELECT
                appointments.id,
                clinics.name,
                appointments.visit_type,
                appointments.amount,
                appointments.created_at
            FROM appointments
            INNER JOIN clinics
                ON clinics.id = appointments.clinic_id
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