import os
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.database import Base, get_session
from src.main import app
from src.models import Ingredient, Recipe

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)


async def get_session_overrides() -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session


app.dependency_overrides[get_session] = get_session_overrides


async def add_test_recipes():
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)()
    recipe1 = Recipe(
        id=1,
        title="recipe1_Test",
        cooking_time=7,
        description="Test",
        ingredients=[Ingredient(name="Test")],
    )
    recipe2 = Recipe(
        id=2,
        title="recipe2_Test",
        cooking_time=9,
        description="Test2",
        ingredients=[Ingredient(name="Test2"), Ingredient(name="Test3")],
    )
    async_session.add_all([recipe1, recipe2])
    await async_session.commit()
    return recipe1.id, recipe2.id


@pytest.fixture()
async def connection():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    recipe_id_1, recipe_id_2 = await add_test_recipes()

    yield recipe_id_1, recipe_id_2
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    os.remove("test.db")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_recipes_200(connection):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/recipes/")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_recipes_filling(connection):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/recipes/")
    assert response.text
    answer = response.json()
    assert answer == [
        {"title": "recipe1_Test", "cooking_time": 7, "id": 1, "views": 0},
        {"title": "recipe2_Test", "cooking_time": 9, "id": 2, "views": 0},
    ]


@pytest.mark.anyio
async def test_recipe_200(connection):
    recipe_id_1, recipe_id_2 = connection

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/recipes/{recipe_id_1}")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_recipe_filling(connection):
    recipe_id_1, recipe_id_2 = connection

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/recipes/{recipe_id_1}")
    answer = response.json()
    assert answer == {
        "title": "recipe1_Test",
        "cooking_time": 7,
        "description": "Test",
        "ingredient_list": ["Test"],
    }


@pytest.mark.anyio
async def test_recipe_views(connection):
    recipe_id_1, recipe_id_2 = connection

    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.get(f"/recipes/{recipe_id_1}")
        response = await ac.get("/recipes/")
    answer = response.json()
    assert answer[0]["views"] == 1


@pytest.mark.anyio
async def test_recipe_rating(connection):
    recipe_id_1, recipe_id_2 = connection

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/recipes/")
    answer = response.json()
    assert answer[0]["id"] == 1

    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.get(f"/recipes/{recipe_id_2}")
        response = await ac.get("/recipes/")
    answer = response.json()
    assert answer[0]["id"] == 2

    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.get(f"/recipes/{recipe_id_1}")
        response = await ac.get("/recipes/")
    answer = response.json()
    assert answer[0]["id"] == 1
