from pydantic import BaseModel


class Site(BaseModel):
    """
    Represents the data structure of a site.
    """

    name: str
    location: str
    price: str
    capacity: str
    rating: float
    reviews: int
    description: str
    