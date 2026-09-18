from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Engine works with either PostgreSQL (postgresql+asyncpg://) or SQLite (sqlite+aiosqlite://)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    # SQLite requires check_same_thread=False and increased busy timeout
    connect_args={"check_same_thread": False, "timeout": 30} if "sqlite" in settings.DATABASE_URL else {}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


async def get_db():
    """Dependency providing a transactional async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all database tables and seed statutory master registry records."""
    import app.db.models  # Ensure all model tables are registered with Base.metadata
    from app.db.models import OfficialRegistryRecordModel
    from sqlalchemy import select

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed official statutory identity records into SQLite DB
    DEFAULT_REGISTRY_RECORDS = [
        {
            "id": "reg-aadhaar-mahesh-0380",
            "document_type": "AADHAAR",
            "document_number": "715293520380",
            "masked_number": "XXXX-XXXX-0380",
            "last_four": "0380",
            "name": "Vilasagaram Mahesh",
            "dob": "11/11/2007",
            "gender": "MALE",
            "father_or_guardian": "Vilasagaram Srinivas",
            "address": "H No 1-96/2, Pegadapalli, Jagtial, Telangana - 505532",
            "pincode": "505532",
            "state": "Telangana",
            "phone": "8125703790",
            "status": "ACTIVE",
            "registry_source": "UIDAI CIDR Master Registry (API Setu Gateway)"
        },
        {
            "id": "reg-aadhaar-ananya-7894",
            "document_type": "AADHAAR",
            "document_number": "982345617894",
            "masked_number": "XXXX-XXXX-7894",
            "last_four": "7894",
            "name": "Ananya Sharma",
            "dob": "14/08/1998",
            "gender": "FEMALE",
            "father_or_guardian": "Rajesh Sharma",
            "address": "D/O Rajesh Sharma, Hyderabad, Telangana - 500081",
            "pincode": "500081",
            "state": "Telangana",
            "phone": None,
            "status": "ACTIVE",
            "registry_source": "UIDAI CIDR Master Registry (API Setu Gateway)"
        },
        {
            "id": "reg-pan-rajesh-1234",
            "document_type": "PAN",
            "document_number": "ABCPK1234F",
            "masked_number": "XXXXX1234F",
            "last_four": "234F",
            "name": "RAJESH KUMAR SHARMA",
            "dob": "15/07/1992",
            "gender": "MALE",
            "father_or_guardian": "ANIL KUMAR SHARMA",
            "address": "Flat 4B, Surya Apartment, Andheri East, Mumbai, Maharashtra - 400069",
            "pincode": "400069",
            "state": "Maharashtra",
            "phone": None,
            "status": "ACTIVE",
            "registry_source": "CBDT / Income Tax Department (API Setu Gateway)"
        },
        {
            "id": "reg-dl-rajesh-2345",
            "document_type": "DRIVING_LICENCE",
            "document_number": "MH0120210012345",
            "masked_number": "MH01XXXX0012345",
            "last_four": "2345",
            "name": "RAJESH KUMAR SHARMA",
            "dob": "15/07/1992",
            "gender": "MALE",
            "father_or_guardian": "ANIL KUMAR SHARMA",
            "address": "Flat 4B, Surya Apartment, Andheri East, Mumbai, Maharashtra - 400069",
            "pincode": "400069",
            "state": "Maharashtra",
            "phone": None,
            "status": "ACTIVE",
            "registry_source": "MoRTH Sarathi National Register (API Setu Gateway)"
        }
    ]

    async with AsyncSessionLocal() as session:
        try:
            for rec_data in DEFAULT_REGISTRY_RECORDS:
                stmt = select(OfficialRegistryRecordModel).where(
                    OfficialRegistryRecordModel.document_number == rec_data["document_number"]
                )
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()
                if not existing:
                    new_rec = OfficialRegistryRecordModel(**rec_data)
                    session.add(new_rec)
            await session.commit()
        except Exception:
            await session.rollback()
