from typing import List, Sequence

import uvicorn
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, sessionmaker

import schemas
from database import Base, engine, get_session
from models import Ingredient, Recipe


app = FastAPI()


async def fill_db(eng):
    app_session = sessionmaker(eng, expire_on_commit=False, class_=AsyncSession)()
    res = await app_session.execute(select(Recipe))
    if res.first():
        return
    cucumber = Ingredient(name="Огурец")
    tomato = Ingredient(name="Помидор")
    salt = Ingredient(name="Соль")
    dumplings = Ingredient(name="Пельмени")
    butter = Ingredient(name="Сливочное масло")
    cereals = Ingredient(name="Овсяные хлопья")
    milk = Ingredient(name="Молоко")
    app_session.add_all(
        [
            Recipe(
                id=1,
                title="Салат с огурцом и помидором",
                cooking_time=7,
                description="Огурец, помидор, лук помыть и порезать средними кусками. Добавить майонез, "
                "соль, перемешать.",
                ingredients=[cucumber, tomato, salt],
            ),
            Recipe(
                id=2,
                title="Жареные пельмени",
                cooking_time=15,
                description="Замороженные пельмени выложить на сковороду, смазанную сливочным маслом. Жарить "
                "15 минут с обеих сторон на среднем огне.",
                ingredients=[dumplings, butter],
            ),
            Recipe(
                id=3,
                title="Каша овсяная",
                cooking_time=25,
                description="В кастрюлю положить овсянку с молоком в соотношении 1:3, варить 20 мин на слабом "
                "огне. Выключить огонь, дать постоять 5 минут под крышкой. Добавить кусок масла.",
                ingredients=[cereals, milk, butter],
            ),
        ]
    )
    await app_session.commit()


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await fill_db(engine)


@app.on_event("shutdown")
async def shutdown():
    # await session.close()
    await engine.dispose()


@app.post("/recipes/", response_model=schemas.RecipeDetails, tags=["Recipes"])
async def recipes_add(
    recipe: schemas.RecipeCreate, session: AsyncSession = Depends(get_session)
) -> Recipe:
    """Создает новый рецепт"""
    new_recipe = Recipe(
        title=recipe.title,
        cooking_time=recipe.cooking_time,
        description=recipe.description,
    )
    for ingredient in recipe.ingredients:
        execution = await session.execute(
            select(Ingredient).filter(Ingredient.name == ingredient)
        )
        ing = execution.scalars().first()
        if ing:
            new_recipe.ingredients.append(ing)
        else:
            new_recipe.ingredients.append(Ingredient(name=ingredient))

    async with session as async_session:
        async_session.add(new_recipe)
        await async_session.commit()

    return new_recipe


@app.get(
    "/recipes/",
    response_model=List[schemas.RecipeMain],
    tags=["Recipes"],
    summary="Return list of recipes",
)
async def recipes_all(session: AsyncSession = Depends(get_session)) -> Sequence[Recipe]:
    """Возвращает список доступных рецептов. Отсортированы по числу просмотров и времени готовки."""
    res = await session.execute(
        select(Recipe).order_by(Recipe.views.desc(), Recipe.cooking_time)
    )
    return res.scalars().all()


@app.get(
    "/recipes/{recipe_id}",
    response_model=schemas.RecipeDetails,
    tags=["Recipes"],
    summary="Return one recipe",
)


async def recipes_one(
        recipe_id: int, session: AsyncSession = Depends(get_session)
    ) -> Recipe | None:
    """Возвращает рецепт с описанием деталей."""
    execution = await session.execute(
        select(Recipe)
        .filter(Recipe.id == recipe_id)
        .options(selectinload(Recipe.ingredients))
    )
    recipe = execution.scalars().first()

    if recipe:
        recipe.views += 1  # Увеличиваем количество просмотров
        session.add(recipe)  # Добавляем обновленный объект в сессию
        await session.commit()  # Сохраняем изменения в базе данных

    return recipe


if __name__ == "__main__":
    uvicorn.run("main:app", port=5000, host="127.0.0.1", reload=True)
