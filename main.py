import asyncio
import dataclasses
import time
from typing import List
from typing import Optional

import orjson
import pydantic
from pydantic import RootModel
from sqlalchemy import ForeignKey, select
from sqlalchemy import String
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from faker import Faker

fake = Faker()


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class PydanticBase(
    MappedAsDataclass,
    DeclarativeBase,
    dataclass_callable=pydantic.dataclasses.dataclass
):
    pass


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    phone_no: Mapped[Optional[str]] = mapped_column(String(100))


class User_Pydantic(PydanticBase):
    __tablename__ = "user_account"

    name: Mapped[str] = mapped_column(String(30))
    phone_no: Mapped[Optional[str]] = mapped_column(String(100))
    id: Mapped[int | None] = mapped_column(primary_key=True, init=False, default=None)


async def normal_dc_with_orjson(async_session: async_sessionmaker[AsyncSession]) -> float:
    stmt = select(User).limit(1000)
    async with async_session() as session:
        res = await session.scalars(stmt)

    t1 = time.perf_counter()
    ret = orjson.dumps(res.all()).decode()
    e_time = time.perf_counter() - t1
    print("e_time normal dc", e_time)
    return e_time
    # print("retr", ret[0:100])
    # print(users[0:3], len(users))


async def pydantic_dc_v2(async_session: async_sessionmaker[AsyncSession]) -> float:
    stmt = select(User_Pydantic).limit(1000)
    async with async_session() as session:
        res = await session.scalars(stmt)

    t1 = time.perf_counter()
    # users = res.all()
    ret = RootModel[List[User_Pydantic]](res.all()).model_dump_json()
    e_time = time.perf_counter() - t1
    print("e_time pydantic dc", e_time)
    return e_time


async def load_objects(async_session: async_sessionmaker[AsyncSession]) -> None:
    async with async_session() as session:
        users = [User(name=fake.name(), phone_no=fake.phone_number()) for _ in range(10000)]
        async with session.begin():
            session.add_all(users)


async def async_main() -> None:
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:password@localhost/sample",
        echo=True,
    )

    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            pass

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    ## RUN THE FOLLOWING LINE ONLY ONCE AND COMMENT ON SUBSEQUENT RUNS
    # await load_objects(async_session)

    ## ACTUAL TEST CODE
    t1 = await normal_dc_with_orjson(async_session)
    t2 = await pydantic_dc_v2(async_session)

    x = t2 / t1
    print(f"normal dc is {x:0.2f}x faster")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(async_main())
