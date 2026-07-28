from ptcg_agent.deck_pool_evaluation import write_pool_csv


def test_pool_csv_records_counts_differences_and_reasons(tmp_path) -> None:
    output = tmp_path / "pool.csv"
    write_pool_csv(
        {
            "decisions": [
                {
                    "id": "baseline",
                    "path": "deck.csv",
                    "hash": "abc",
                    "decision": "keep",
                    "roles": ["baseline", "top"],
                    "reason": "retained",
                }
            ]
        },
        output,
    )
    text = output.read_text()
    assert "baseline,deck.csv,abc,keep,baseline|top,retained" in text
