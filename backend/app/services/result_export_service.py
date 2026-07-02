import json
from pathlib import Path

from app.config.config import settings


class ResultExportService:

    OUTPUT_DIR = Path(
        settings.RESULTS_FOLDER
    )

    @classmethod
    def save_result(
        cls,
        metadata: dict
    ):

        cls.OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        output_file = (
            cls.OUTPUT_DIR /
            "latest_result.json"
        )

        export_data = {

            "title":
            metadata.get(
                "title",
                metadata.get(
                    "reel_title",
                    ""
                )
            ),

            "description":
            metadata.get(
                "description",
                metadata.get(
                    "reel_description",
                    ""
                )
            ),

            "hashtags":
            metadata.get(
                "hashtags",
                metadata.get(
                    "reel_hashtags",
                    []
                )
            ),

            "highlights":
            metadata.get(
                "all_highlights",
                metadata.get(
                    "highlights",
                    []
                )
            ),

            "stats":
            metadata.get(
                "stats",
                {}
            ),

            "final_reel":
            metadata.get(
                "final_reel",
                ""
            ),

            "vertical_reel":
            metadata.get(
                "vertical_reel",
                ""
            ),

            "thumbnail":
            metadata.get(
                "thumbnail",
                ""
            ),

            "result_json":
            str(
                output_file
            )

        }

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                export_data,
                file,
                indent=4
            )

        print(
            "RESULT JSON SAVED:",
            output_file
        )

        return str(
            output_file
        )