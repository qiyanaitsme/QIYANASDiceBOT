from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Boolean, text
import json

with open('config.json') as f:
    config = json.load(f)

engine = create_async_engine(config['db_url'], echo=True)
Base = declarative_base()
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Room(Base):
    __tablename__ = 'rooms'
    
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    password = Column(String, nullable=True)
    player1_id = Column(Integer, nullable=True)
    player2_id = Column(Integer, nullable=True)
    player1_name = Column(String, nullable=True)
    player2_name = Column(String, nullable=True)
    player1_score = Column(Integer, default=0)
    player2_score = Column(Integer, default=0)
    player1_attempts = Column(Integer, default=0)
    player2_attempts = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def cleanup_rooms():
    async with async_session() as session:
        await session.execute(text("DELETE FROM rooms WHERE is_active = false"))
        await session.commit()
