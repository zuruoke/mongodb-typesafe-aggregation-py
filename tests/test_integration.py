"""Runs every stage against a real MongoDB.

Skipped unless ``MONGODB_URI`` is set. Each run seeds a throwaway database and drops it after:

    MONGODB_URI=mongodb://localhost:27018 uv run pytest -m integration
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from typing import Any, TypedDict

import pytest

from mongodb_typesafe_aggregation import PipelineBuilder
from mongodb_typesafe_aggregation.types.filter import filter

pymongo = pytest.importorskip("pymongo")

pytestmark = pytest.mark.integration


class Supplier(TypedDict):
    name: str
    region: str


class Product(TypedDict):
    name: str
    price: float
    description: str
    stock: int
    category: str
    tags: list[str]
    supplier: Supplier
    active: bool
    relatedProductIds: list[Any]


class Order(TypedDict):
    productId: Any
    quantity: int
    customerName: str
    status: str


@pytest.fixture(scope="module")
def db() -> Iterator[Any]:
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        pytest.skip("set MONGODB_URI to run integration tests")

    client: Any = pymongo.MongoClient(uri, serverSelectionTimeoutMS=3000)
    name = f"mta_test_{uuid.uuid4().hex[:12]}"
    database = client[name]
    try:
        _seed(database)
        yield database
    finally:
        client.drop_database(name)
        client.close()


def _seed(database: Any) -> None:
    laptop, phone, chair = database.products.insert_many(
        [
            {
                "name": "Laptop",
                "price": 999.99,
                "description": "High-performance laptop",
                "stock": 50,
                "category": "electronics",
                "tags": ["portable", "work"],
                "supplier": {"name": "TechHub", "region": "EU"},
                "active": True,
            },
            {
                "name": "Smartphone",
                "price": 599.99,
                "description": "Latest model smartphone",
                "stock": 100,
                "category": "electronics",
                "tags": ["mobile"],
                "supplier": {"name": "MobileMax", "region": "US"},
                "active": True,
            },
            {
                "name": "Office Chair",
                "price": 249.99,
                "description": "Ergonomic office chair",
                "stock": 20,
                "category": "furniture",
                "tags": ["office", "comfort"],
                "supplier": {"name": "HomePro", "region": "US"},
                "active": False,
            },
        ]
    ).inserted_ids
    for product_id, related in [(laptop, [phone, chair]), (phone, [laptop]), (chair, [])]:
        database.products.update_one({"_id": product_id}, {"$set": {"relatedProductIds": related}})

    database.orders.insert_many(
        [
            {"productId": laptop, "quantity": 2, "customerName": "John Doe", "status": "pending"},
            {
                "productId": phone,
                "quantity": 1,
                "customerName": "Jane Smith",
                "status": "completed",
            },
            {
                "productId": laptop,
                "quantity": 3,
                "customerName": "Bob Johnson",
                "status": "pending",
            },
        ]
    )
    database.archived_products.insert_one({"name": "Legacy Tablet", "price": 149.99})


def run(db: Any, collection: str, builder: PipelineBuilder[Any]) -> list[dict[str, Any]]:
    return list(db[collection].aggregate(builder.build()))


def test_match_with_filter_operators(db: Any) -> None:
    docs = run(
        db,
        "products",
        PipelineBuilder(Product).match(
            price=filter(float).gte(200).lte(1000),
            category=filter(str).in_(["electronics", "furniture"]),
            active=True,
        ),
    )
    assert sorted(doc["name"] for doc in docs) == ["Laptop", "Smartphone"]


def test_lookup_add_fields_project(db: Any) -> None:
    docs = run(
        db,
        "products",
        PipelineBuilder(Product)
        .match(name="Laptop")
        .lookup("orders", local_field="_id", foreign_field="productId", as_="orders")
        .add_fields(orderedQuantity={"$sum": "$orders.quantity"})
        .project(
            _id=0,
            name=1,
            orderedQuantity=1,
            remainingStock={"$subtract": ["$stock", "$orderedQuantity"]},
        ),
    )
    assert docs == [{"name": "Laptop", "orderedQuantity": 5, "remainingStock": 45}]


def test_lookup_with_pipeline(db: Any) -> None:
    pending = PipelineBuilder(Order).match(
        {"$expr": {"$eq": ["$productId", "$$pid"]}}, status="pending"
    )
    docs = run(
        db,
        "products",
        PipelineBuilder(Product)
        .lookup("orders", let={"pid": "$_id"}, pipeline=pending, as_="pending")
        .project(_id=0, name=1, pending={"$size": "$pending"})
        .sort(name=1),
    )
    assert docs == [
        {"name": "Laptop", "pending": 2},
        {"name": "Office Chair", "pending": 0},
        {"name": "Smartphone", "pending": 0},
    ]


def test_unwind_group_sort(db: Any) -> None:
    docs = run(
        db,
        "orders",
        PipelineBuilder(Order)
        .lookup("products", local_field="productId", foreign_field="_id", as_="product")
        .unwind("$product")
        .group(
            _id="$status",
            totalOrders={"$sum": 1},
            revenue={"$sum": {"$multiply": ["$quantity", "$product.price"]}},
        )
        .sort(totalOrders=-1),
    )
    assert [(doc["_id"], doc["totalOrders"]) for doc in docs] == [
        ("pending", 2),
        ("completed", 1),
    ]
    assert docs[0]["revenue"] == pytest.approx(4999.95)


def test_sort_skip_limit(db: Any) -> None:
    docs = run(db, "products", PipelineBuilder(Product).sort(price=-1).skip(1).limit(1))
    assert [doc["name"] for doc in docs] == ["Smartphone"]


def test_count(db: Any) -> None:
    assert run(db, "products", PipelineBuilder(Product).match(active=True).count("n")) == [{"n": 2}]


def test_facet(db: Any) -> None:
    docs = run(
        db,
        "products",
        PipelineBuilder(Product).facet(
            expensive=lambda p: p.match(price=filter(float).gt(700)).project(_id=0, name=1),
            total=lambda p: p.count(),
        ),
    )
    assert docs == [{"expensive": [{"name": "Laptop"}], "total": [{"count": 3}]}]


def test_unwind_with_array_index(db: Any) -> None:
    docs = run(
        db,
        "products",
        PipelineBuilder(Product)
        .match(name="Office Chair")
        .unwind("$tags", include_array_index="position")
        .project(_id=0, tags=1, position=1),
    )
    assert docs == [{"tags": "office", "position": 0}, {"tags": "comfort", "position": 1}]


def test_replace_root(db: Any) -> None:
    docs = run(
        db,
        "products",
        PipelineBuilder(Product).replace_root("$supplier").cast(Supplier).sort(name=1),
    )
    assert [doc["name"] for doc in docs] == ["HomePro", "MobileMax", "TechHub"]


def test_set_and_unset(db: Any) -> None:
    docs = run(
        db,
        "products",
        PipelineBuilder(Product)
        .set(isExpensive=filter(bool).cond({"$gt": ["$price", 500]}, True, False))
        .unset(["_id", "description", "supplier", "tags", "relatedProductIds"])
        .match(isExpensive=False),
    )
    assert docs == [
        {
            "name": "Office Chair",
            "price": 249.99,
            "stock": 20,
            "category": "furniture",
            "active": False,
            "isExpensive": False,
        }
    ]


def test_union_with(db: Any) -> None:
    archived = PipelineBuilder().project(_id=0, name=1)
    docs = run(
        db,
        "products",
        PipelineBuilder(Product).project(_id=0, name=1).union_with("archived_products", archived),
    )
    assert sorted(doc["name"] for doc in docs) == [
        "Laptop",
        "Legacy Tablet",
        "Office Chair",
        "Smartphone",
    ]


def test_graph_lookup(db: Any) -> None:
    docs = run(
        db,
        "products",
        PipelineBuilder(Product)
        .graph_lookup(
            "products",
            start_with="$relatedProductIds",
            connect_from_field="relatedProductIds",
            connect_to_field="_id",
            as_="related",
            max_depth=0,
        )
        .project(_id=0, name=1, related={"$size": "$related"})
        .sort(name=1),
    )
    assert docs == [
        {"name": "Laptop", "related": 2},
        {"name": "Office Chair", "related": 0},
        {"name": "Smartphone", "related": 1},
    ]


def test_bucket(db: Any) -> None:
    docs = run(
        db,
        "products",
        PipelineBuilder(Product).bucket(
            "$price", [0, 300, 700, 1000], output={"names": {"$push": "$name"}}
        ),
    )
    assert docs == [
        {"_id": 0, "names": ["Office Chair"]},
        {"_id": 300, "names": ["Smartphone"]},
        {"_id": 700, "names": ["Laptop"]},
    ]


def test_bucket_auto(db: Any) -> None:
    docs = run(db, "products", PipelineBuilder(Product).bucket_auto("$price", 3))
    assert [doc["count"] for doc in docs] == [1, 1, 1]
    assert docs[0]["_id"]["min"] == 249.99


def test_redact(db: Any) -> None:
    active = {"$eq": ["$active", True]}
    docs = run(
        db,
        "products",
        PipelineBuilder(Product).redact(
            {"$cond": {"if": active, "then": "$$KEEP", "else": "$$PRUNE"}}
        ),
    )
    assert sorted(doc["name"] for doc in docs) == ["Laptop", "Smartphone"]


def test_merge(db: Any) -> None:
    run(
        db,
        "orders",
        PipelineBuilder(Order)
        .group(_id="$customerName", quantity={"$sum": "$quantity"})
        .merge("customer_totals", when_matched="replace", when_not_matched="insert"),
    )
    totals = {doc["_id"]: doc["quantity"] for doc in db.customer_totals.find()}
    assert totals == {"John Doe": 2, "Jane Smith": 1, "Bob Johnson": 3}
