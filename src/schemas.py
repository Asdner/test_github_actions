from typing import List

from pydantic import BaseModel, Field


class BaseRecipe(BaseModel):
    title: str = Field(..., title="Название блюда")
    cooking_time: int = Field(..., title="Время приготовления, мин")


class RecipeCreate(BaseRecipe):
    ...,
    description: str = Field(..., title="Описание рецепта")
    ingredients: List[str] = Field(..., title="Ингредиенты")


class RecipeMain(BaseRecipe):
    id: int
    views: int = Field(..., title="Количество просмотров рецепта")

    class Config:
        orm_mode = True


class RecipeDetails(BaseRecipe):
    description: str = Field(..., title="Описание рецепта")
    ingredient_list: List[str] = Field(..., title="Список ингредиентов")

    class Config:
        orm_mode = True
