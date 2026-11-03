from mongodb_typesafe_aggregation.stages import match_stage


class TestMatchStage:
    def test_wraps_query(self) -> None:
        assert match_stage({"status": "active"}) == {"$match": {"status": "active"}}

    def test_copies_query(self) -> None:
        query: dict[str, object] = {"status": "active"}
        stage = match_stage(query)
        query["price"] = 1

        assert stage == {"$match": {"status": "active"}}
